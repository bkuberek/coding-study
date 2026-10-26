# cstudy CLI

The `cstudy` command for coding-study. Product docs: [`docs/`](../docs/README.md); command reference: [`docs/specs/cli.md`](../docs/specs/cli.md); development workflow and checks: [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Run

The project is defined by the root `pyproject.toml` (the installable `coding-study` distribution, [install](../docs/specs/installation-and-workspaces.md#install)); its sources are in `cli/src/`. From the checkout:

```sh
uv sync                                  # creates .venv at the repository root
uv run cstudy init ~/cstudy-dev-workspace        # a workspace outside the checkout
export CSTUDY_WORKSPACE=~/cstudy-dev-workspace
uv run cstudy doctor --fix
uv run cstudy verify --conformance
```

A checkout is its own content root, so `uv run cstudy` reads this repository's `problems/`, `tracks/`, `runners/` and `schemas/`, and builds with the workspace's toolchains. To put this checkout's `cstudy` on `PATH` (editable, so changes apply without reinstalling):

```sh
uv tool install --editable .
```

## Progress

| Command | Does |
|---------|------|
| `cstudy stats [--by pattern\|track\|lang\|difficulty] [--since DATE] [--json]` | Per group: problems, attempted, passed, mastered, pass rate, median solve time, weakness; then finished attempts, the last 7 days, the streak, due reviews and the latest bench verdicts |
| `cstudy mock [--minutes 45] [--count 2] [--track T]... [--lang L]` | Starts new medium and hard problems from different groups with one shared timer; `cstudy hint` and `cstudy solution` stay locked until it ends or every problem is done |
| `cstudy export [--out PATH]` | Writes every `progress.db` row to `progress-export.json` (one row per line, safe to commit) |
| `cstudy import [PATH]` | Restores an export into an empty `progress.db`; refuses a database that holds progress |

Definitions: [progress-and-scheduling](../docs/specs/progress-and-scheduling.md#statistics).

## Test options

| Option | Does |
|--------|------|
| `cstudy test --stress N [--seed S]` | Concurrent problems: N runs per stress case and variant. Function and design problems: N extra generated inputs checked against the oracle approach; `--stress 1 --seed S` reruns one |
| `cstudy test --json` | The run as one JSON document on standard output; notices go to standard error |

Reference: [`docs/specs/cli.md#cstudy-test`](../docs/specs/cli.md#cstudy-test).

## Develop

The tool settings live in `cli/`: `ruff.toml`, `pyrightconfig.json`, `pytest.ini` and `.importlinter` (a `pyproject.toml` here would make uv treat `cli/` as a project of its own). Run from `cli/`:

| Check | Command |
|-------|---------|
| Tests | `uv run pytest -q` |
| Fast tests (no real Gradle, Node, tsc or workspace venv) | `uv run pytest -q -m "not slow"` |
| Slow tests | `uv run pytest -q -m slow`: they set up one temporary workspace per session (`uv sync`, `pnpm install`, a Gradle build), never one in the checkout |
| Lint and format | `uv run ruff check` and `uv run ruff format --check` |
| Types (strict on `src/`) | `uv run pyright` |
| Layer contracts | `uv run lint-imports` |

## Layout

| Package | Holds | May import |
|---------|-------|------------|
| `coding_study.domain` | Pure rules: problem, signature and type DSL models, cases, comparators and judging, naming and file layout, statements and hints, static checks and ready criteria, time limits, attempts and grades, scheduling, the weakness score and `cstudy next` selection, `cstudy stats` statistics, `cstudy new` scaffolds, config and setting precedence | standard library only, no I/O modules |
| `coding_study.application` | Ports (`ports.py`), the `Environment` a command runs in, and one use case per command (`start_attempt.py`, `run_tests.py`, `complete_attempt.py`, `next_problem.py`, `reveal_hint.py`, `new_problem.py`, `verify_content.py`, `doctor.py`, ...) | domain |
| `coding_study.adapters` | Filesystem problems, workspace and caches; JSON Schema validation; TOML config; SQLite progress store and its migrations (`sqlite/`); one package per language under `languages/` (stub generators and runner adapters); the subprocess runner and tool probes; git change detection; the `cstudy new` templates (`templates/`); the `cstudy init` workspace template (`workspace_template/`); content and workspace resolution (`locations.py`), the workspace marker and setup, the runner runtime (`runner_runtime.py`); `environment_factory.py`, which builds the real `Environment` | application, domain, libraries |
| `coding_study.entrypoints` | The `cstudy` launcher (`launcher.py`), the Typer app (`cli.py`), one module per command in `commands/`, and the exit codes and error mapping (`shared.py`) | everything |

The import-linter contracts in `.importlinter` enforce the table. Tests mirror the packages under `tests/`; `tests/fakes.py` builds an `Environment` on a temporary root with in-memory runners, and `tests/workspaces.py` sets up real workspaces for the slow tests.
