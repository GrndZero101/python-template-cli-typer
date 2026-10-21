# TODO

Enhancements found while building projects from this template. Each names where it came from,
so the working code can be copied rather than rewritten. Remove an entry once it has landed.

## From tboss-svc-pki (2026-10-21)

Source: `C:\shares\projects\private\tools\tboss-svc-pki`, commit `59b3a53` unless noted, and
its `docs/DECISIONS.md` (D23, D24 and "Gotchas").

### 1. Rich error output, with a hint (D24)

`run_app` prints usage errors with click's plain `exc.show()`, and `cli.py.jinja` writes
`Error: ...` with `sys.stderr.write`, so errors look like argparse beside typer's rich help.

- `typer_entrypoint.py`: at a terminal, show a `ClickException` with
  `typer.rich_utils.rich_format_error(exc)`, typer's own red Error panel; elsewhere keep
  `exc.show()`. `run_app` takes `console: Console = err` to decide, so a test can pass
  `Console(file=io.StringIO(), force_terminal=True)` instead of patching.
- `output.py`: add `error_panel(message, hint)` and `print_error(message, hint=None,
  console=err)`. A panel titled Error with a `Hint:` line at a terminal; plain `Error: ...` and
  `Hint: ...` lines otherwise, never wrapped, so a path in a log stays copyable and tests can
  match it.
- Use `print_error` in `cli.py.jinja`, `_show_help_for_missing`, and the `status.py`
  reference, and say in the SKILL's rules that a runtime error names what to try.
- Tests: `tests/test_output.py` and the two new tests at the end of
  `tests/test_typer_entrypoint.py` in tboss-svc-pki.
- tboss-svc-pki already has all of this, so its next `copier update` will merge it as a silent
  duplicate rather than a conflict; check for doubled definitions there.
