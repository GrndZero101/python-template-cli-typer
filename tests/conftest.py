"""Fixtures shared by the generation tests."""

import os
import subprocess
from pathlib import Path

import pytest

BASE_REPOSITORY = "https://github.com/GrndZero101/python-template"


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
    destination = tmp_path_factory.mktemp("base") / "python-template"
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
