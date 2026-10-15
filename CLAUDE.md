# Working on this template repository

This repo is the **CLI layer** of a two-layer [copier](https://copier.readthedocs.io/) template: a
typer command-line tool, its tests and the skills that teach a model to extend it. The root is
**not** a Python project.

The other layer is the **base**, the repository
[python-template-base](https://github.com/GrndZero101/python-template-base): the hooks, `tools/`, `CLAUDE.md`,
the shared skills and the gate. This layer's one `_tasks` entry applies the base to the same
directory, so one `copier copy` of this repo yields both layers, each with its own answers file.

**The rules for the code shipped here are the base's `template/CLAUDE.md`**, and `template/` is
held to exactly that standard: no nested defs, no `print`, `pathlib` and explicit encodings,
`raise ... from e`, and the rest. Read it in the base repository, or in any generated project, where
it is the project's `CLAUDE.md`. This repo does not copy the base's machinery, so none of those rules
is enforced here as you type; the generated project's gate enforces them, and `tests/` runs it.

## Layout

| Path | What it is |
|---|---|
| `template/` | What a generated project receives from this layer. Holds Jinja; not runnable in place. |
| `copier.yml` | This layer's questions, exclusions and its one task, which applies the base. |
| `tests/test_template.py` | Generates projects and runs their gate. The only check on `template/`. |
| `tests/conftest.py` | The `base_checkout` fixture: where the tests find the base template. |
| `.pre-commit-config.yaml` | Governs **this** repo, which has no `tools/` of its own. |
| `pyproject.toml` | Dev deps and lint config for the root. Not published, not importable. |
| `examples/` | Specs for building a CLI on the scaffold, to measure whether the skills carry. |

**Every generated file has exactly one owner**: it is rendered by the base or by this layer, never
both. Two templates rendering the same path conflict on `copier update` (markers in the file), so
the split is by directory and a test checks it. This layer owns `pyproject.toml`, `README.md`,
`src/`, `tests/`, `.copier-answers.yml`, `.claude/rules/cli-typer.md` and the skills
`python-cli-typer`, `python-data` and `python-tui`. The base owns everything else, including its own
fallback `pyproject.toml` under `_skip_if_exists`, which copier never overwrites. Adding a file here
that the base renders breaks the contract test; ask in the base repository first.

A file under `template/` carries a `.jinja` suffix only when it must name something the answers
decide:

- the project files `pyproject.toml`, `README.md` and `.copier-answers.yml`;
- `cli.py` and `config.py`, which hold the script name and the environment-variable prefix;
- `conftest.py` and the test modules under `tests/`, which import the package by name;
- the reference tests in `.claude/skills/python-cli-typer/reference/`, for the same reason: they
  are copied into `tests/` unchanged, so they must already name the package.

Everything else ships literally. The source modules manage it because their internal imports are
**relative**, so nothing inside `src/` names the package and copier only has to render the directory
name. Keep it that way: an absolute import there would force another file to become a template.
Anything that needs the script name should import it from `config.py` rather than render it again.

## The gate

`template/` cannot be checked in place: it holds Jinja and has no `pyproject.toml`, so `ruff` would
fall back to default rules and `ty` would find no environment. What covers it instead is
`tests/test_template.py`. It generates projects — at the default Python and at the floor — and runs
**that project's** gate and test suite inside each. It costs about a minute, so it runs at commit
only when the commit touches `template/`, `tests/`, `copier.yml`, `pyproject.toml` or `uv.lock`.
`SKIP=generation-tests git commit -m "..."` skips it deliberately.

The suite needs the base. `BASE_TEMPLATE_DIR` names a checkout of python-template-base; without it the
tests use the base on GitHub. Set it when the change under test depends on an unpushed base change:

```bash
BASE_TEMPLATE_DIR=~/projects/github/GrndZero101/python-template-base uv run pytest
```

Copier includes uncommitted working-tree changes when a template is a local path (it warns
`DirtyLocalWarning`), so the tests validate what you are about to commit, not the last commit.

The base's own CI checks this repo out and runs this suite against the base commit under test, so a
base change that breaks this layer fails there. This repo's CI does the reverse and checks out the
base's `main` into `base/`. Both run on Linux, Windows and macOS; the Windows and macOS jobs are the
only check of the portability rules away from WSL, so do not trim the matrix.

## Commands

Run from the repo root:

```bash
prek run --all-files            # the whole gate, generation tests included (~1 min)
uv run pytest                   # generation tests only
uv run pytest -k gate           # only the generated project's gate, when iterating
copier copy --trust --defaults -d base_template="$BASE_TEMPLATE_DIR" . /tmp/scratch
```

Run the linters **through prek, never directly**: the hooks pin their own versions. First-time
setup needs all three shims, or the commit-message check and `git merge --no-ff` into `main` break:

```bash
prek install -t pre-commit -t commit-msg -t pre-merge-commit
```

## Branching

Never edit on `main`, and `main` receives only merge commits. Nothing here enforces the first rule
as you type: check `git status --short --branch` before the first edit and branch with
`git switch -c <type>/<short-name>`. Commits are [Conventional Commits](https://www.conventionalcommits.org/)
— `type(scope): summary`, imperative, lower case, no period, at most 72 characters — which
`conventional-pre-commit` checks, and `no-commit-to-branch` refuses a commit on `main`. Finish a
branch by squashing it to one commit and merging with `git merge --no-ff -m "<what the work does>"`;
the merge subject describes the work, never `Merge branch '...'`.

The base's `tools/finish_branch.py` does the squash, the gate and the merge in one step, and the
base's `git-workflow` skill explains why. Run it from a clone of the base against this directory,
or do the three steps by hand.
