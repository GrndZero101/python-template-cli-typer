# python-template-cli-typer

A [copier](https://copier.readthedocs.io/) template for a Python command-line tool, built around one
idea: every rule in the generated `CLAUDE.md` exists so a human (or an AI agent) can stop the
program and inspect it. Structure, debuggability and portability rules are mechanically enforced by
lint config and a `prek` gate — not just documented and hoped for.

This is the CLI layer of a two-layer template. It supplies the typer application, its tests and the
skills that teach a model to extend it. The other layer is the base,
[python-template-base](https://github.com/GrndZero101/python-template-base): the rule set, a `PreToolUse`
guard that refuses edits to `main`, a `PostToolUse` gate that lints on every save, a `Stop` gate
that re-checks every changed file and runs the tests before a turn can end, `ruff`/`ty`/`rumdl`/
`prek` configured, and a custom checker for the conventions no linter covers. Copying this
template applies the base too, so one command yields both.

## Quickstart

Once per machine: git, uv, and copier and prek as uv tools. Then one command makes a project with
the git repo, the venv and the hooks already wired. Generation makes the project's first commit, so
git needs your name and email first, if it has none: `git config --global user.name "..."`, and
the same for `user.email`.

### Linux, macOS or WSL

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # then open a new shell, so uv is on PATH
uv tool install --upgrade copier     # installs it, or upgrades one already there
uv tool install --upgrade prek
copier copy --trust gh:GrndZero101/python-template-cli-typer my-project     # answer the prompts
cd my-project
```

### Windows (PowerShell)

```powershell
winget install --id Git.Git -e      # git, if you have none
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# open a new terminal, so uv is on PATH
uv tool install --upgrade copier     # installs it, or upgrades one already there
uv tool install --upgrade prek
copier copy --trust gh:GrndZero101/python-template-cli-typer my-project     # answer the prompts
cd my-project
```

### Then, on either

Check the project and start work:

```bash
prek run --all-files --skip no-commit-to-branch   # should be all green
uv run pytest
git switch -c feat/first-thing                    # never work on main
```

CI generates projects and runs their gate and tests on Windows, but the Windows install steps
above have not yet been walked through end to end on a fresh machine.

---

## Path A — start a new project from this template

```bash
copier copy --trust gh:GrndZero101/python-template-cli-typer my-project     # answer the prompts
cd my-project
```

`--trust` is required because the template declares `_tasks` — the ones that run `git init`,
`uv sync` and install the shims. Without it copier exits 4 with "Template uses potentially unsafe
feature: tasks".

That is the whole setup. Generation already ran `git init -b main`, `uv sync`, the initial commit,
and all three `prek` shims. Verify and start work:

```bash
prek run --all-files --skip no-commit-to-branch   # should be all green
uv run pytest
git switch -c feat/first-thing                    # never work on main
```

You will be asked for: project name, package name, console script name, description, author name
and email, minimum Python version (3.12, 3.13 or 3.14), licence (MIT, Apache-2.0 or Proprietary),
the name on its copyright line, and CI (`none` or `github`).

**CI** defaults to `none`, which ships nothing, so a project on GitLab or with no CI is free to add
its own. `github` ships one `.github/workflows/ci.yml` that runs `prek run --all-files` and
`uv run pytest` on pushes to `main` and on pull requests, on Linux only: on a private repository
macOS and Windows minutes cost more, so they are commented in. To change the answer later, pass it
to both layers' updates, `-d ci=github`; a layer given no answer keeps the one it recorded.

**Answer your name and email once.** Copier reads a personal settings file and offers its
`defaults` as the default answer to any question of the same name, in every template. It lives at
`~/.config/copier/settings.yml` on Linux, `~/Library/Application Support/copier/settings.yml`
on macOS and `%LOCALAPPDATA%\copier\settings.yml` on Windows, or wherever `COPIER_SETTINGS_PATH`
says. To fill it from your git identity, if you have none yet (on macOS, use that path instead):

```bash
mkdir -p ~/.config/copier
cat > ~/.config/copier/settings.yml <<EOF
defaults:
  author_name: "$(git config user.name)"
  author_email: "$(git config user.email)"
EOF
```

On Windows, in PowerShell:

```powershell
$dir = "$env:LOCALAPPDATA\copier"
New-Item -ItemType Directory -Force $dir | Out-Null
$yaml = @"
defaults:
  author_name: "$(git config user.name)"
  author_email: "$(git config user.email)"
"@
[IO.File]::WriteAllText("$dir\settings.yml", $yaml)    # UTF-8 without a BOM, in any PowerShell
```

You are still asked; the file only changes what Enter accepts. An update keeps the answers you
recorded and ignores it. For an email that stays private, use GitHub's noreply address,
`<id>+<username>@users.noreply.github.com`, shown under Settings > Emails.

Every project is a CLI on typer, pydantic-settings, rich and loguru, with a scaffold: one
placeholder `about` command, with global and command flags that each resolve flag, then
environment variable, then config file, then default. A command that crunches data files or draws
a full-screen interface is added on top of it, following the `python-data` or `python-tui` skill,
rather than chosen at generation.

The base also works alone, for a prototype or a repo adopting the guards:
`copier copy --trust gh:GrndZero101/python-template-base my-project`.

### Keeping it in sync with the template

A project records one source per layer, each in its own answers file, and each layer updates
separately, touching only its own files:

| Layer | Answers file | Command |
|---|---|---|
| The base | `.copier-answers.base.yml` | `copier update --trust -a .copier-answers.base.yml` |
| This one, the CLI | `.copier-answers.yml` | `copier update --trust` |

Run both, the base first: this layer is written against the base, so a change here that needs a
base change then never lands ahead of it. Each update needs a clean tree, so commit between them:

```bash
git status --short                    # must be clean; copier refuses otherwise
git switch -c chore/template-update   # branch first; main takes no direct commits

copier update --trust -a .copier-answers.base.yml   # the base: a three-way merge into the tree
# resolve conflicts, if any (below)
uv sync                               # before any check; see below
git diff                              # review; nothing is committed for you
git add -A                            # -A, not -a: the template may have added files
git commit -m "chore(template): update python-template-base to <commit>"

copier update --trust                 # this layer
# resolve, sync, review and commit as above, naming python-template-cli-typer

uv run python tools/finish_branch.py "chore(template): update from the templates"
```

`<commit>` is the `_commit` value copier just wrote to that layer's answers file.
`finish_branch.py` squashes the branch, runs the gate and the tests, and merges it into `main`.

The base's setup helper runs this whole flow as one command, from a clone of
[python-template-base](https://github.com/GrndZero101/python-template-base):
`sh bootstrap.sh update my-project`, with `--finish` to merge too. It stops at a conflict and says
how to carry on; [its README](https://github.com/GrndZero101/python-template-base#keeping-it-in-sync-with-the-template)
has the details.

**`--trust` runs nothing on an update.** It lets a template run its `_tasks`, and copier asks for
it whenever a template declares any, exiting 4 without it. Every task here is guarded to run on
`copy` only, so an update runs none of them. An agent can run the update too, but it cannot answer
copier's prompts: give it `--defaults`, with new questions answered explicitly (below). Run it in a
terminal of your own when you want copier to ask.

**`uv sync` before any check.** A dependency the template dropped stays installed in `.venv` until
you sync. `ty` then still resolves an import that `pyproject.toml` no longer provides, and the gate
passes code that a fresh clone fails. `httpx` once did exactly that.

**New questions.** Interactively, `copier update` re-asks every question, using your recorded answer
as the default. Add `--skip-answered` (`-A`) to be asked only the ones you have not yet answered,
which means the questions the template has added since your last update. Under `--defaults`, a new
question silently takes the template's default, and that can be wrong. When `script_name` was
added, `--defaults` recorded the name derived from the package rather than the command the project
already had, and the update proposed renaming it in every file that carried it. For a
non-interactive update, answer new questions explicitly with
`--defaults --data script_name=my-cli`. Afterwards, `git diff .copier-answers.yml` shows any new
key, and each one is a question that was just answered for you.

**Conflicts.** Updates are a three-way merge: your edits survive wherever they don't overlap the
template's. Where they do, copier writes git-style inline markers: the project's version opens with
`<<<<<<< before updating`, and the new template render closes with `>>>>>>> after updating`. Copier
also records the file as unmerged, so `git status` lists it under *Unmerged paths* and the
usual tools work: `git checkout --ours <file>` keeps the project's version, `git checkout --theirs
<file>` takes the new template render, and `git add <file>` marks the file resolved. Taking a side
replaces the whole file, though, not just the conflicted hunks, so `--theirs` also drops any
project-only lines *outside* the markers. Use it only on a file you never meant to diverge;
otherwise resolve hunk by hunk.

While any file still holds markers, the edit-time gate pauses. A save lists the conflicted files
instead of reporting syntax errors from each one. `check-merge-conflict` blocks the commit if any
markers remain.

To pin a version, or to move deliberately, pass a commit. The template has no release tags yet;
once it does, `copier update` moves to the latest tag rather than the newest commit.

```bash
copier copy --trust --vcs-ref <commit> gh:GrndZero101/python-template-cli-typer my-project
copier update --trust --vcs-ref <commit>
```

Do not delete either answers file — `copier update` reads it to know what you answered.

---

## Path B — work on the template itself

```bash
git clone https://github.com/GrndZero101/python-template-cli-typer
cd python-template-cli-typer
uv sync
prek install -t pre-commit -t commit-msg -t pre-merge-commit
```

All three shims are required. `prek install` alone wires only `pre-commit`, which silently skips
the commit-message check and breaks `--no-ff` merges into `main`.

```bash
git switch -c feat/whatever    # never edit on main; nothing here enforces it for you
```

Edit under `template/`, then:

```bash
uv run pytest                   # generate projects, run their gate and suite
uv run pytest -k gate           # only the generated project's gate, while iterating
prek run --all-files            # the whole gate, generation tests included
```

The tests need the base template. Without configuration they use the base on GitHub; to test
against a checkout of it, for a change that depends on an unpushed base change:

```bash
BASE_TEMPLATE_DIR=~/projects/github/GrndZero101/python-template-base uv run pytest
```

To look at real output rather than an assertion:

```bash
copier copy --trust --defaults -d project_name=Scratch -d package_name=scratch \
  -d base_template="$BASE_TEMPLATE_DIR" . /tmp/scratch
```

**The template cannot be linted or run where it sits** — it holds Jinja and has no
`pyproject.toml`. The generation tests are the only thing that verifies it, which is why they are
wired into the gate.
See [CLAUDE.md](CLAUDE.md) for why, and for the branching and merge rules.

## Layout

- **`template/`** — the CLI layer: what a generated project receives from this repo.
- **`copier.yml`** — this layer's questions and its one task, which applies the base.
- **`tests/test_template.py`** — generates projects and runs their gates. The only check on the
  template.
- **`examples/`** — specs for building a CLI on the scaffold, to measure whether the skills carry.
- **`.pre-commit-config.yaml`** — the gate for this repository.

## License

[MIT](LICENSE)
