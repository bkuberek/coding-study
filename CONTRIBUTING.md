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
| JVM tests | `uv run pytest -q -m jvm` (the `slow` tests that drive Gradle, javac, kotlinc or a JVM runner on the JDK your shell selects) |
| All tests | `uv run pytest -q` (the `slow` tests drive real Gradle, Node, tsc and a workspace venv in a temporary workspace) |

CI runs on Linux for every push to a branch and every pull request ([versioning](docs/specs/versioning.md#what-the-workflow-does)). The fast checks are the first six rows, plus `cstudy verify --static`. The JVM job runs the JVM tests and `cstudy verify --conformance` for `--lang java` and for `--lang kotlin`, on JDK 21 and on JDK 26, the two ends of the supported range. Two more jobs run only when the `changes` job finds that the diff can affect them: the browser tests on Chromium, and the `sandbox` job, `pytest -m "docker and not docker_jvm"` on a real Docker engine. The real-engine JVM tests carry the `docker_jvm` marker, together with `docker`, and stay a local gate so that the job fits its 15 minutes: `uv run pytest -q -m docker` is the full local run and includes them (about 20 minutes under load), and a new test that builds a JVM project on a real engine takes the marker too. The other `slow` tests, and `cstudy verify` of a catalog service project over real stacks, stay a local gate. A test belongs to the JVM job when it carries the `jvm` marker, together with `slow`: mark a new test that drives the JVM the same way, and a row of a test over every language with `jvm_marked` from `cli/tests/toolchains.py`.

Changes to content, runners or code generation also need `cstudy verify` (with `CSTUDY_WORKSPACE` set):

| Change | Gate |
|--------|------|
| Runners or stub generation | `uv run cstudy verify --conformance`, then a full `uv run cstudy verify` |
| Problems in `problems/` | `uv run cstudy verify --changed --oracle --ladder --require-ready` |
| Items in `tracks/` | `uv run cstudy verify --track system-design --require-ready` (or `--track code-review`) |

`--ladder` measures timing, so run it on an idle machine on AC power; a busy machine reports lower confidence. Optional: run the problem gate in a `pre-push` git hook.

### Which JDK

Java and Kotlin build and run with the JDK your shell selects, 21 to 26 ([toolchains guide](docs/guides/toolchains.md#jdk)), so the `slow` tests and `cstudy verify` use that one. To try another JDK for one command, set `JAVA_HOME` for it, for example with SDKMAN: `JAVA_HOME="$HOME/.sdkman/candidates/java/<identifier>" uv run pytest -q -m slow`. CI runs the JVM tests and the Java and Kotlin conformance suites on JDK 21 and on JDK 26 on every push. Before a release that changes the range or the JVM build, the local gate also runs a full `cstudy verify` of the Java and Kotlin references on both ([ADR 0016](docs/decisions/0016-jdk-range.md#verification)).

One build wants an exact JDK: `tools/ide-launcher/build.sh`, which rebuilds the IntelliJ launcher jar, needs javac 21, since javac 17 and 21 emit other bytes for the same `--release 17`, and a slow test compares the committed jar with a rebuild. The script uses the JDK that `JAVA_HOME` names, else the first `javac` on `PATH`, and says how to select a 21 when it finds another: `JAVA_HOME="$HOME/.sdkman/candidates/java/<identifier of a 21>" tools/ide-launcher/build.sh`. The test skips itself on any other JDK, so run it with `JAVA_HOME` at a 21 to check the jar.

## Authoring content

Problem statements, tests, hints and solutions must be original ([ADR 0004](docs/decisions/0004-original-problem-wording.md)); a LeetCode problem appears only as a link in `references.leetcode`.

1. Scaffold the problem in the checkout: `uv run cstudy new <slug> --from-template array|tree|design|progressive|concurrent`. Run from a development checkout, `cstudy new` writes into the repository's `problems/`, not into the workspace named by `CSTUDY_WORKSPACE` (a follow-up to know about when you test with a scratch workspace).
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
