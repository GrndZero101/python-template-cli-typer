"""Shared output plumbing for every subcommand: the output formats and the two consoles.

Data goes to `out` (stdout); anything decorative or human-facing goes to `err` (stderr). The
format changes only when the caller asks, never because stdout is a pipe.

Why two consoles, and why the format never changes on its own: .claude/skills/python-cli-typer/reference/output.md.
"""

from enum import StrEnum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

out = Console()  # data only — stdout
err = Console(stderr=True)  # progress, status, human-facing errors


class OutputFormat(StrEnum):
    """How to render a command result."""

    table = "table"
    json = "json"


def error_panel(message: str, hint: str | None = None) -> Panel:
    """Return an error as typer draws its own: a red panel titled Error, the hint below."""
    text = Text(message)
    if hint:
        text.append("\n")
        text.append("Hint: ", style="bold yellow")
        text.append(hint)
    return Panel(text, title="Error", title_align="left", border_style="red")


def print_error(message: str, hint: str | None = None, console: Console = err) -> None:
    """Print an error for a person: a panel at a terminal, plain lines anywhere else.

    A log or a pipe gets `Error: ...` on one line, never wrapped, so a path in it can be
    copied and a test can match it. The hint says what to try, so give one whenever the fix is
    knowable: the path to check, the flag to pass, the variable to set.
    """
    if console.is_terminal:
        console.print(error_panel(message, hint))
        return
    console.file.write(f"Error: {message}\n")
    if hint:
        console.file.write(f"Hint: {hint}\n")
