r"""Open a file in the user's editor and wait for it to close.

typer 0.27's vendored click has no `click.edit()`, and that one ran a shell anyway, so this is the
replacement. The editor is `$VISUAL`, then `$EDITOR`, then a fallback: Notepad on Windows, and
elsewhere the first of nvim, vim, vi and nano on PATH. A variable may carry arguments, as
`code --wait` needs, and on Windows a quoted path, as `"C:\Program Files\Neovim\bin\nvim.exe"` needs.

It runs as an argument list with no shell, so nothing in the variable is interpreted beyond
splitting it into words. On Windows a `.cmd` launcher, such as VS Code's `code`, is found by its
full path on PATH, which Windows runs without a shell of its own.
"""

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

EDITOR_VARIABLES = ("VISUAL", "EDITOR")
WINDOWS_FALLBACK = ("notepad",)
POSIX_FALLBACKS = ("nvim", "vim", "vi", "nano")

type Which = Callable[[str], str | None]
type Runner = Callable[[Sequence[str]], int]


class EditorError(RuntimeError):
    """No editor could be found or started. The message names the variable to set."""


def split_command(value: str, platform: str = sys.platform) -> list[str]:
    """Split an editor variable into words, honouring quotes the way the platform's shell does.

    Windows paths keep their backslashes: POSIX-style splitting would read them as escapes.
    """
    if platform != "win32":
        return shlex.split(value)
    words = shlex.split(value, posix=False)
    return [word[1:-1] if len(word) > 1 and word[0] == word[-1] == '"' else word for word in words]


def _fallback(platform: str, which: Which) -> list[str]:
    """Return the editor to use when no variable names one."""
    if platform == "win32":
        return list(WINDOWS_FALLBACK)
    for name in POSIX_FALLBACKS:
        if which(name) is not None:
            return [name]
    msg = f"no editor found: set VISUAL or EDITOR, e.g. EDITOR=nvim; none of {POSIX_FALLBACKS}"
    raise EditorError(msg)


def editor_command(
    environ: Mapping[str, str] = os.environ,
    platform: str = sys.platform,
    which: Which = shutil.which,
) -> list[str]:
    """Return the editor's command line, without the file, its program resolved on PATH."""
    words: list[str] = []
    for variable in EDITOR_VARIABLES:
        value = environ.get(variable, "").strip()
        if value:
            words = split_command(value, platform)
            break
    if not words:
        words = _fallback(platform, which)
    program = which(words[0])
    if program is None:
        msg = f"editor {words[0]!r} is not on PATH; set VISUAL or EDITOR to one that is"
        raise EditorError(msg)
    return [program, *words[1:]]


def _run(command: Sequence[str]) -> int:
    """Run `command` attached to this terminal and return its exit code."""
    # An argument list with its program resolved on PATH, never a shell string.
    return subprocess.run(command, check=False).returncode  # ruff: ignore[subprocess-without-shell-equals-true]


def edit_file(path: Path, command: Sequence[str], run: Runner = _run) -> None:
    """Open `path` with the editor `command` and wait for the editor to exit."""
    argv = [*command, str(path)]
    try:
        code = run(argv)
    except OSError as exc:
        msg = f"could not start {argv[0]}: {exc}; set VISUAL or EDITOR to a working editor"
        raise EditorError(msg) from exc
    if code != 0:
        msg = f"{argv[0]} exited with status {code}; {path} may not be saved"
        raise EditorError(msg)
