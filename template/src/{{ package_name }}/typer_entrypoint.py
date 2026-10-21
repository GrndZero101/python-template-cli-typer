"""Run a typer app and return an exit code instead of calling sys.exit.

typer 0.27 no longer depends on the `click` package — it vendors its own fork
at `typer._click`, so the exception types this needs are not part of typer's
public API. This module isolates that one private import so it exists in a
single place if a future typer release changes it.
"""

import contextlib
import sys

import typer
from rich.console import Console
from typer._click.exceptions import (  # ruff: ignore[import-private-name]
    ClickException,
    MissingParameter,
    NoArgsIsHelpError,
)
from typer.rich_utils import rich_format_error

from .output import err, print_error


def _show_error(exc: ClickException, console: Console) -> None:
    """Print a usage error: typer's rich panel at a terminal, click's plain lines elsewhere.

    Plain lines keep a long message whole in a log, where a panel would wrap it. `console`
    says only whether stderr is a terminal; typer's formatter opens its own on stderr.
    """
    if console.is_terminal:
        rich_format_error(exc)
        return
    exc.show()


def _show_help_for_missing(exc: MissingParameter, console: Console) -> None:
    """Print the command's full help, then the error, both to stderr.

    With rich installed, typer's help formatter prints straight to stdout and `get_help()`
    returns an empty string, so stdout is redirected around the call. rich looks `sys.stdout`
    up at write time, so the redirect catches it; the plain formatter returns its text instead,
    which is echoed to stderr explicitly.
    """
    if exc.ctx is None:
        _show_error(exc, console)
        return
    with contextlib.redirect_stdout(sys.stderr):
        help_text = exc.ctx.get_help()
    if help_text:
        typer.echo(help_text, err=True, color=exc.ctx.color)
    print_error(exc.format_message(), console=console)


def run_app(
    app: typer.Typer, argv: list[str] | None, prog_name: str, console: Console = err
) -> int:
    """Invoke `app` with `argv` and translate its result into an exit code.

    With `standalone_mode=False`, typer's own dispatch (`typer/core.py::_main`)
    already catches an internally raised `typer.Exit` and *returns* its exit
    code rather than re-raising it — the exit code never reaches this frame
    as an exception. Only a genuine usage error (`ClickException`, e.g. an
    unknown flag) still propagates as one.

    A bare invocation of a `no_args_is_help=True` app raises `NoArgsIsHelpError`
    (a `ClickException` with exit_code 2) after printing help — that is a
    request for help, not a usage error, so it is translated to exit code 0.

    A command missing a required argument raises `MissingParameter`, whose own
    `.show()` prints only a terse usage line. The full help is more useful, so it
    is printed instead, followed by the error. At a terminal every error is typer's
    rich panel; in a pipe or a log it is plain lines, whole. It is still a usage
    error, though: the exit code stays 2 and everything goes to stderr, so
    `tool cmd && next` stops and nothing lands in a pipe.

    `console` decides only whether stderr is a terminal; a test passes
    `Console(file=io.StringIO(), force_terminal=True)` to see the panel path.
    """
    try:
        result = app(args=argv, standalone_mode=False, prog_name=prog_name)
    except NoArgsIsHelpError as exc:
        exc.show()
        return 0
    except MissingParameter as exc:
        _show_help_for_missing(exc, console)
        return int(exc.exit_code)
    except ClickException as exc:
        _show_error(exc, console)
        return int(exc.exit_code)
    return int(result) if isinstance(result, int) else 0
