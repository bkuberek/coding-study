# Contributing

This guide covers changes to coding-study itself: the `cstudy` CLI, the runners, and the bundled content. To practice, or to write problems only for yourself, use an installed `cstudy` and a workspace instead ([README](README.md#quickstart)).

## Quick path

1. Clone the repository and install the development environment:

   ```bash
   git clone https://github.com/bkuberek/coding-study
   cd coding-study
   uv sync                                  # creates .venv at the repository root
   ```

2. Create a development workspace outside the checkout and point `cstudy` at it:

   ```bash
   uv run cstudy init ~/cstudy-dev-workspace
   export CSTUDY_WORKSPACE=~/cstudy-dev-workspace
   uv run cstudy doctor --fix
   ```

3. Make your change, run the [checks](#checks), and commit with a [Conventional Commit](#commits-and-versions) message.

`uv run cstudy` in a checkout reads the checkout's `problems/`, `tracks/`, `runners/` and `schemas/`, and builds with the workspace's toolchains. To put the checkout's `cstudy` on your `PATH`, run `uv tool install --editable .`.

## Never commit solutions or progress

This repository holds code and content only, never a workspace. Your practice files, notes, attempts and `progress.db` belong in your own workspace repository.

- `cstudy init` refuses to create a workspace inside the checkout unless you pass `--force`.
- The root `.gitignore` ignores `.cs/`, `.statements/`, `progress.db*`, `progress-export.json`, and practice directories at the root (`python/`, `typescript/`, `jvm/`, `notes/`, `.archive/`, `workspace/`) as a second guard.
- Reference solutions under `problems/<id>-<slug>/solutions/` are content, not practice: they are the answers `cstudy solution` shows.

## Checks

Run the CLI checks from `cli/`; its tool settings live there (`ruff.toml`, `pyrightconfig.json`, `pytest.ini`, `.importlinter`). Every check must pass before you commit.

| Check | Command |
|-------|---------|
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format --check .` |
| Types (strict on `src/`) | `uv run pyright` |
| Layer contracts | `uv run lint-imports` |
| Fast tests | `uv run pytest -q -m "not slow"` |
| All tests | `uv run pytest -q` (the `slow` tests drive real Gradle, Node, tsc and a workspace venv in a temporary workspace) |

Changes to content, runners or code generation also need `cstudy verify` (with `CSTUDY_WORKSPACE` set):

| Change | Gate |
|--------|------|
| Runners or stub generation | `uv run cstudy verify --conformance`, then a full `uv run cstudy verify` |
| Problems in `problems/` | `uv run cstudy verify --changed --oracle --ladder --require-ready` |
| Items in `tracks/` | `uv run cstudy verify --track system-design --require-ready` (or `--track code-review`) |

`--ladder` measures timing, so run it on an idle machine on AC power; a busy machine reports lower confidence. Optional: run the problem gate in a `pre-push` git hook.

## Authoring content

Problem statements, tests, hints and solutions must be original ([ADR 0004](docs/decisions/0004-original-problem-wording.md)); a LeetCode problem appears only as a link in `references.leetcode`.

1. Scaffold the problem in the checkout: `uv run cstudy new <slug> --from-template array|tree|design|progressive|concurrent`.
2. Follow the [authoring workflow](docs/specs/authoring.md#workflow): the statement in `problem.md`, the signature in `meta.yaml`, the cases in `tests.json`, a brute-force Python oracle, `generator.py`, the optimal approaches in Python, TypeScript, Java, and Kotlin, and `solutions/explanation.md`. The [problem format](docs/specs/problem-format.md) defines every file.
3. Set `status: ready` once the problem passes the ready gate:

   ```bash
   uv run cstudy verify <slug> --oracle --ladder --require-ready
   ```

Non-autograded items (system design, code review) follow the [item workflow](docs/specs/authoring.md#item-workflow). Slugs are unique across `problems/` and `tracks/` and never change once merged, because progress is keyed on the slug.

## Commits and versions

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org), and the commit types drive the version ([versioning](docs/specs/versioning.md)):

| Commit | Version change while `0.x` |
|--------|----------------------------|
| `fix:`, `perf:` | Patch |
| `feat:`, and breaking changes (`feat!:`, `BREAKING CHANGE:`) | Minor |
| `docs:`, `chore:`, `ci:`, `build:`, `refactor:`, `style:`, `test:` | None |

Examples: `feat(cli): add cstudy stats --since`, `fix(runners): report a missing symbol as a load error`, `docs: clarify the workspace layout`. On every push to `main`, a GitHub workflow bumps `pyproject.toml`, updates `CHANGELOG.md`, and tags the release; never edit the version by hand.

Keep tests and docs in the same commit as the behavior they cover. Specs in `docs/specs/` are normative: when the code and a spec disagree, fix one of them in the same change.

## Where to read next

| Read | For |
|------|-----|
| [Architecture](docs/architecture.md) | Hexagonal boundaries, ports and adapters, data flows |
| [`cli/README.md`](cli/README.md) | The CLI's package layout |
| [Documentation index](docs/README.md) | Every spec and decision record |
