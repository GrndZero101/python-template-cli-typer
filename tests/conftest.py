"""Fixtures shared by the generation tests."""

import os
import subprocess
from pathlib import Path

import pytest
from plumbum import local

BASE_REPOSITORY = "https://github.com/GrndZero101/python-template-base"

# Git's variables that tie a command to one repository, as `git rev-parse --local-env-vars` lists
# them. A git hook exports GIT_INDEX_FILE=.git/index, so when the commit runs generation-tests,
# every git command the suite starts inherits it. copier runs `git --git-dir=<clone>` from this
# repo's root, which then stages the clone's objects into THIS repo's index, leaving it pointing at
# blobs it does not have (seen in the base on 2026-10-18: "invalid object ... for 'TODO.md'").
GIT_REPOSITORY_VARIABLES = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
)


def pytest_configure() -> None:
    """Drop the variables a git hook set, so no git command here can reach the hook's repository.

    From plumbum's environment too: copier runs git through plumbum, which copied `os.environ` when
    pytest-copie, a plugin, imported it, before any conftest ran.
    """
    for name in GIT_REPOSITORY_VARIABLES:
        os.environ.pop(name, None)
        if name in local.env:
            del local.env[name]


@pytest.fixture(scope="session")
def base_checkout(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a checkout of the base template, for the tests that read or snapshot its files.

    `BASE_TEMPLATE_DIR` names one already, which is how the base's own CI runs this suite against
    the commit under test. Without it the base is cloned from GitHub, so the suite also runs
    from a bare clone of this repo.
    """
    named = os.environ.get("BASE_TEMPLATE_DIR")
    if named:
        return Path(named)
    destination = tmp_path_factory.mktemp("base") / "python-template-base"
    cloned = subprocess.run(
        ["git", "clone", "--quiet", BASE_REPOSITORY, str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cloned.returncode == 0, (
        f"could not clone {BASE_REPOSITORY}: {cloned.stderr}; "
        "set BASE_TEMPLATE_DIR to a local checkout of the base template"
    )
    return destination
