# Configuration: flag, then environment variable, then config file, then default

The one home for why settings work as they do in `config.py` and `options.py`. Read before adding a
setting in an unusual way, or when a flag or variable does not win when it should.

Every setting resolves in that order, and `pydantic-settings` does the merge — never hand-roll it.
The config file is the subject of its own section below.
The scaffold's `config.py` is the worked instance:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="forbid")

    verbose: bool = False
    output: OutputFormat = OutputFormat.table
```

The mechanism rests on one fact: **a value passed to the `Settings` constructor beats the
environment**, which beats the field default. So a flag wins simply by arriving as a constructor
argument — and an absent flag must not arrive at all. Hence:

- **Every option that maps to a setting defaults to `None`**, meaning "not given". A typer default of
  `False` or `table` is indistinguishable from the user typing it, and the environment variable
  could then never win.
- **`load_settings` drops the `None`s** before constructing. It builds the overrides in a
  `TypedDict`, not a `dict`: ty checks `Settings(**overrides)` against pydantic-settings' own
  typed `_env_prefix`-style parameters and rejects a loosely typed dict.
- **A boolean flag needs both halves**, `--verbose/--no-verbose`, typed `bool | None`. Without
  `--no-verbose` there is no way to override `VERBOSE=1` from the command line.
- **The prefix is the script name**, upper-cased: `my-tool` reads `MY_TOOL_OUTPUT`. A generic
  `CLI_OUTPUT` would be shared by every tool on the machine.
- **Do not also pass typer's `envvar=`.** click would parse the variable with its rules and
  pydantic with its own, and they disagree at the edges (`"yes"`, `"on"`). Name the variable in the
  help text instead, built from `env_var(field)` so it cannot drift. Write it `(env: NAME)`: typer
  renders help as rich markup, and `[env var: NAME]` is taken for a style tag and vanishes.
- **A validation failure exits 2** with a message naming the value, the flag *and* the variable,
  because the caller may have set either. `cli.main` maps `SettingsError` to that.
- **No `.env` file by default.** A stray `.env` in the working directory would change a test's
  outcome. Opt in with `env_file=".env"` when the tool genuinely needs it.
- **Tests clear the prefix.** The scaffold's `conftest.py` deletes every `<PREFIX>_*` variable
  before each test, so a developer's shell cannot make a test pass or fail.

**Secrets** are the one exception to "every setting has a flag":

- **Never a flag.** A flag's value is visible in shell history and to anyone who can list
  processes, so a secret field is left out of `_Overrides`, `load_settings` and `options.py`; it
  comes from its variable or the config file. The wiring tests find secret fields with
  `secret_fields()` and exempt them from those steps. A validation error masks its value.
- **`SecretStr`, so incidental exposure is masked.** Its `repr` is `SecretStr('**********')` and
  `model_dump(mode="json")` gives `'**********'`, so the debug log of the resolved settings and
  `about`'s table and JSON never show it. Discoverability comes from `about`, which still lists
  the field and its variable.
- **Unwrap once, at the point of use.** `.get_secret_value()` where the client is built, or in a
  command that exists to output the secret. Such a command emits it raw, JSON included, as
  `terraform output -json` and `gh auth token` do: there the reveal is the point, and the explicit
  call makes it greppable.
- **Never in a URL.** `http_client.py` logs each request's URL at debug; a header is not logged.

**The config file** (`config_file.py`) holds a user's standing preferences, below the
environment so a variable can still override it for one run:

- **YAML, keyed by field name**, parsed with `yaml.safe_load` by `ConfigFileSource`, which hands
  the raw values to pydantic, so one validation pass covers every layer. Not pydantic-settings'
  `YamlConfigSettingsSource`: it cannot take a path chosen at run time, and a file holding a list
  escapes it as a bare `ValueError`. PyYAML is YAML 1.1: an unquoted
  `no`, `off` or `yes` is a boolean. A field typed `str` rejects it rather than storing `"False"`,
  but the fix is quoting, so say so in any example a user copies.
- **Unknown keys are an error naming the file**, as `extra="forbid"` makes them for the other
  sources. A typo in a config file must not be silently ignored.
- **`config` is itself a setting**: `--config` beats `<PREFIX>_CONFIG`, which beats the default
  location. `ConfigFileSource` runs after the init and environment sources and reads the resolved
  value from `current_state`; the file cannot name itself. A file named this way must exist; the
  default need not, and `about` shows which path is in use.
- **The default location is where CLI users look**: `$XDG_CONFIG_HOME/<script>/config.yaml` when
  that is set and absolute, on every platform; otherwise `~/.config/<script>/config.yaml`, macOS
  included, rather than `~/Library/Application Support`; and `%APPDATA%` on Windows, the roaming
  profile, because settings should follow the user.
- **Tests never read the developer's file.** `conftest.py` points `XDG_CONFIG_HOME` into
  `tmp_path` for every test; a test that needs a file writes one there, or passes `--config`.
- **No project-local file by default** (`./<script>.yaml`). It would make the working directory
  change a command's behaviour, which is the surprise the `.env` default avoids. A tool that acts
  on a dataset, rather than on the user's behalf, does want one beside the data: "A workspace
  file" below.

**File-only settings** (`FILE_ONLY_FIELDS`) are the second exception to "every setting has a
flag", after secrets. A mapping of models, such as named profiles, has no sensible flag or
variable spelling, so it is set in the file alone. Its error names the path inside the file
(`profiles.home.format`), not a flag. Recipe in the skill.

Global options live on `@app.callback()`, which stores what it was given in a frozen
`GlobalOptions` on `ctx.obj`. Each command calls `load_settings(global_options(ctx), ...)` once,
with its own flags as keywords, so settings are validated in one place and the command body sees a
single typed `Settings`, never a raw `ctx.obj`.

**The global options travel whole, and `load_settings` requires them.** When each command copied
the globals into `load_settings` one keyword at a time, adding `--config` meant editing every
command, and a command that missed the edit accepted `--config` and silently ignored it — which a
real project's update did. Now a new global option is a field on `GlobalOptions` and reaches every
command untouched, and a command that forgets the argument fails `ty` and raises `TypeError`
rather than quietly dropping the flags. Where there is no command line, pass `GlobalOptions()`.

Do not merge a command's overrides into existing settings with `model_copy(update=...)` — it skips
validation entirely. Construct a new `Settings`.

## A command that repairs the config file

The app callback loads settings before any command runs, so a broken config file stops every
command, including `config edit` or `init`, whose job is to fix or create it. Name those commands
in `cli.py` and return from the callback before loading:

```python
# Commands that must run while the config file is missing or invalid: fixing it is their job.
WITHOUT_CONFIG_FILE = ("config", "init")

@app.callback()
def configure(ctx: typer.Context, *, verbose: VerboseOption = None, ...) -> None:
    options = GlobalOptions(verbose=verbose, config=config)
    ctx.obj = options
    if ctx.invoked_subcommand in WITHOUT_CONFIG_FILE:
        configure_logging(verbose=bool(verbose))
        return
    settings = load_settings(options)
    configure_logging(verbose=settings.verbose)
```

Such a command finds the file without reading it: `--config`, then `<PREFIX>_CONFIG`, then
`default_config_path`, the order `Settings` resolves `config` in. Write that as a `config_path`
function in `config.py`, with the environment as a parameter, and test that it agrees with
`load_settings(...).config` for a valid file. Open it with `editor.py` from the skill's
references, then call `load_settings` to validate what the user saved and report any mistake as
an ordinary `SettingsError`. Seed a missing file with every setting commented out, so the user
edits a list of what exists rather than an empty file.

## A workspace file

For a tool that works on a folder of data, such as a ledger, a site or a set of statements, the
data's own settings belong beside it, in a file found the way git finds `.git`:

- **Found by walking up from the current folder** to the first `<script>.yaml`, so a command run
  anywhere inside the folder uses it. `--workspace PATH` (a global option) or
  `<PREFIX>_WORKSPACE` names one instead, and must then exist; a searched-for one need not.
- **Precedence**: flag, variable, workspace file, user config file, default. One
  `ConfigFileSource` reads both files and returns `{**user, **workspace}`, so there is still one
  validation pass. Which keys each file may hold can differ: tool-wide preferences in the user
  file, the dataset's profiles in the workspace file; reject a key in the wrong file by name.
- **A relative path in it is relative to the workspace folder**, never to the current folder, so
  the file works from any folder below it and the tree can be moved. Anchor paths when the file
  is read, before validation, so the model only ever sees absolute paths.
- **The search start is a parameter**: `ConfigFileSource(..., cwd=Path.cwd())` in
  `settings_customise_sources`, and `find_workspace(start)` a plain function. Its tests pass a
  folder under `tmp_path`.
- **Tests must not find the developer's workspace**: add `monkeypatch.chdir(tmp_path)` to the
  autouse fixture in `conftest.py` beside the `XDG_CONFIG_HOME` one, or running the suite from
  inside a workspace changes its results.
- **`about` shows which workspace file is in effect**, as it shows the config path.
