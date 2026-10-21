# Output: `--output` and the two consoles

Why every command takes `--output`, why its default never changes on its own, and why there are two
rich consoles. Read before writing anything to stdout or stderr.

## The `--output` contract

Every command that emits data takes `--output`/`-o`. Minimum set: `table` (human) and `json`
(machine). Add `ndjson` for streams and `csv` where consumers want it.

```python
class OutputFormat(StrEnum):
    """How to render a command result."""

    table = "table"
    json = "json"
```

Declare a reusable annotated alias once, in `options.py`, then put it on **each command**. Its
default is `None`, not `table` — see **Configuration** below for why:

```python
OutputOption = Annotated[
    OutputFormat | None,
    typer.Option("--output", "-o", help=f"Output format. (env: {env_var('output')})"),
]


def ls(ctx: typer.Context, output: OutputOption = None) -> None:
    """List records."""
    settings = load_settings(global_options(ctx), output=output)
    emit(fetch_records(), settings.output)
```

**Do not declare `--output` only on `@app.callback()`.** A callback option is parsed at the *group*
level, so `tool -o json ls` works but `tool ls -o json` fails with `No such option: -o` — and the
second is where people actually type it. Verified on typer 0.27. The alias costs one line per
command and puts the flag where it is expected.

Reserve the callback for options that genuinely belong to the group, like `--verbose` or
`--config`. If you want `--output` accepted in both positions, you need it in both places plus
explicit precedence — usually not worth the ambiguity.

**The default never changes on its own.** `table` on a terminal, `table` in a pipe. Colour and
spinners auto-suppress when stdout is not a tty, but the *data format* only changes when the caller
asks — via `-o json` or the `<PREFIX>_OUTPUT=json` variable. This is deliberate: a tool that
silently emits JSON when redirected behaves differently in CI than in the terminal where you tested
it, and the failure is invisible. rich already honours `NO_COLOR` and `TERM=dumb`, so that half is
free.

For `json`, write it directly rather than through rich — no console configuration can then break it:

```python
def emit(rows: list[Record], fmt: OutputFormat, console: Console) -> None:
    """Write results to stdout in the requested format."""
    if fmt is OutputFormat.json:
        sys.stdout.write(json.dumps([r.model_dump(mode="json") for r in rows]) + "\n")
        return
    console.print(_build_table(rows))
```

One JSON object or array per invocation. On the error path stdout stays **empty**.

## Two rich consoles — the sharpest edge in this stack

`rich.Console()` writes to **stdout** by default, and so do `Progress` and `status`. So the obvious
`console.print("Fetching…")` silently corrupts the stream a caller is parsing. Declare both, once:

```python
out = Console()  # data only — stdout
err = Console(stderr=True)  # progress, status, human-facing errors
```

Everything decorative goes to `err`. Progress bars must also disable themselves when there is no
terminal, or CI logs fill with redraw frames:

```python
with Progress(console=err, disable=not err.is_terminal) as progress:
    ...
```

If you find yourself passing `out` to anything other than the final result render, that is the bug.

## Errors for a person: `print_error`

typer draws a usage error as a red panel titled Error at a terminal, and `run_app` keeps that. A
runtime error written with `sys.stderr.write("Error: ...")` beside it looks like argparse, so
`output.py` has `print_error(message, hint=None, console=err)`, which matches the panel at a
terminal and prints `Error: ...` and `Hint: ...` as whole lines anywhere else. The lines are never
wrapped: a path in a log stays copyable, and a test matches `f"Error: {path} ..."` exactly.

```python
except (OSError, UnicodeDecodeError, ValueError) as exc:
    logger.opt(exception=exc).debug("could not read {}", path)
    print_error(f"could not read {path}: {exc}", hint="it needs a header row and UTF-8 text")
    raise typer.Exit(RUNTIME_FAILURE) from exc
```

The hint says what to try, and it has to be true, so repeat the contract the argument's help
already states rather than guessing at the cause. A test of the panel passes
`Console(file=io.StringIO(), force_terminal=True)` as `console`; `tests/test_output.py` has both
paths.

## ASCII marks, colour for the verdict

`✓`, `✗`, `→` and `·` in text raise `UnicodeEncodeError: 'charmap' codec can't encode` through
rich's legacy Windows renderer when stdout is cp1252, which it is under an agent's shell on Windows.
rich degrades its own box-drawing characters safely; glyphs inside your text it passes straight to
the stream. Mark a verdict with `OK`, `FAIL`, `->` and `-` and let the colour carry the meaning,
which `NO_COLOR` and a pipe then strip without losing the words.
