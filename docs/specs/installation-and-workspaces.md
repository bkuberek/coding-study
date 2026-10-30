# Spec: Installation and Workspaces

`cstudy` is a tool you install, and you practice in a **workspace**: a directory of your own, versioned in its own git repository if you want, that holds your solutions, notes and progress. The tool ships the **content** (problems, tracks, runners, schemas and the workspace templates), so this repository never doubles as a workspace and solutions are never committed to it by accident ([ADR 0008](../decisions/0008-installable-tool-and-separate-workspaces.md)).

## Install

```bash
brew install bkuberek/tap/cstudy
uv tool install git+https://github.com/bkuberek/coding-study
pipx install git+https://github.com/bkuberek/coding-study
```

Homebrew installs a release: its wheel from the GitHub release, into a virtual environment on Homebrew's Python 3.13, with the runtime dependencies pinned in `uv.lock` ([ADR 0013](../decisions/0013-homebrew-distribution.md), [Homebrew tap](versioning.md#homebrew-tap)). Installing by full name (`bkuberek/tap/cstudy`) works on a fresh machine; Homebrew 7 refuses other commands on the tap, such as `brew info cstudy`, until `brew trust bkuberek/tap` has been run once. uv and pipx build the project at the repository root of the default branch. A content author works from a checkout instead: `uv run cstudy ...` in the checkout, or `uv tool install --editable .` to put that checkout's `cstudy` on `PATH`.

When several installs exist, the first `cstudy` on `PATH` runs; Homebrew warns when an earlier `PATH` entry shadows its `cstudy`. No install method brings the language toolchains: [install the language toolchains](../guides/toolchains.md), then run `cstudy doctor`.

| Item | Rule |
|------|------|
| Distribution | `coding-study`, defined by the root `pyproject.toml` (hatchling); the `cstudy` script |
| Wheel | `coding_study/` from `cli/src/coding_study/`, plus `coding_study/content/{problems,tracks,runners,schemas}` from the repository root |
| Release files | The wheel and `requirements.txt` (the runtime dependencies from `uv.lock`, with hashes), attached to the GitHub release of each version ([versioning](versioning.md#github-release)) |
| sdist | The same top-level paths as the checkout (`cli/src`, `problems`, `tracks`, `runners`, `schemas`), so a wheel built from the sdist equals one built from the checkout |
| Excluded | Build output and caches (`node_modules`, `build`, `.gradle`, `.kotlin`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `target`) and `runners/python/tests` |
| Workspace templates | Package data in `coding_study/adapters/workspace_template/`: the practice projects with the Gradle wrapper and lock files, and the root `go.work` |

## Content root

The content root holds `problems/`, `tracks/`, `runners/` and `schemas/`. `cstudy` reads it and never writes to it, except `cstudy new` in a checkout.

| Order | Source | Used for |
|-------|--------|----------|
| 1 | `--content PATH` (global flag) | An author verifying a checkout with an installed `cstudy` |
| 2 | `CSTUDY_CONTENT` | Same, from the environment |
| 3 | The bundled copy (`coding_study/content/`) | Any installed `cstudy` |
| 4 | The source checkout `cstudy` runs from (`cli/src/coding_study` two levels below a directory with `problems/` and `schemas/`) | `uv run cstudy` and editable installs in a checkout |

A root given by flag or variable must contain `problems/` and `schemas/`, or the command exits 3. A checkout found by rule 1, 2 or 4 is **editable**: `cstudy new` writes into it. The bundled copy is read-only.

## Workspace root

| Order | Source |
|-------|--------|
| 1 | `--workspace PATH` (global flag) |
| 2 | `CSTUDY_WORKSPACE` |
| 3 | The nearest directory, from the current one upward, that holds `.cs/workspace.toml` |
| 4 | The current directory |

The marker `.cs/workspace.toml` makes a directory a workspace. Every command that needs one (all but `cstudy init`, `cstudy doctor`, `cstudy list` and `cstudy show`) exits 3 when the resolved directory has no marker: `no coding-study workspace at <dir> (no .cs/workspace.toml): run cstudy init`. Outside a workspace, `cstudy list` and `cstudy show` read the catalog with empty progress and keep their caches in `$XDG_CACHE_HOME/coding-study/catalog/` (default `~/.cache/coding-study/catalog/`); `cstudy doctor` checks the toolchains only.

### Marker

```toml
# coding-study workspace (docs/specs/installation-and-workspaces.md); keep it in version control.
schema = 1
created_with = "0.1.0"
```

| Key | Meaning |
|-----|---------|
| `schema` | Workspace layout version; this `cstudy` supports `1`. A newer schema fails `cstudy doctor` (upgrade `cstudy`) and every command that needs a workspace exits 3 |
| `created_with` | The `cstudy` version that ran `cstudy init`; `cstudy doctor` prints it next to the running version |

### Layout

```text
<workspace>/
  .cs/workspace.toml      # marker (tracked)
  .cs/ide.json            # digests of the IDE files cstudy wrote (tracked)
  .cs/runtime/            # materialized runners and the IntelliJ launcher (ignored, per machine)
  .cs/                    # index, cases, calibration, build, runs caches (ignored)
  .gitignore, README.md
  .vscode/, .idea/        # IDE project files: tasks, run and debug configurations, SDK settings
  python/                 # pyproject.toml (dev tools: pyright, ruff, debugpy), uv.lock, practice/<snake_slug>.py
  typescript/             # package.json, pnpm-lock.yaml, tsconfig.json, support.ts, practice/<slug>.ts
  jvm/                    # Gradle wrapper, settings.gradle.kts, java/ and kotlin/ subprojects
  go/                     # go.mod (module workspace, Go 1.24), practice/<snake_slug>/<snake_slug>.go
  go.work                 # use ./go, so gopls and the go command find go/ from the root
  rust/                   # Cargo.toml (package practice, one [[example]] per started problem), .cargo/config.toml, lib.rs, practice/<snake_slug>.rs
  notes/                  # answers to non-autograded items
  problems/               # your own problems, overlaid on the catalog
  .archive/               # previous attempts (tracked)
  .statements/            # rendered statements (ignored)
  progress.db             # SQLite, created on first use (ignored; cstudy export backs it up)
```

Every path `cstudy` prints for a workspace file is relative to the workspace root (`python/practice/two_sum.py`, `.statements/two-sum.md`). `progress_db` in the config file is relative to it too.

## cstudy init

```text
cstudy init [PATH] [--git] [--force] [--ide vscode|idea]... [--no-ide]
```

Creates a workspace in `PATH` (default: `--workspace`, then `CSTUDY_WORKSPACE`, then the current directory), creating the directory when needed.

| Step | Rule |
|------|------|
| Refusals (exit 3) | `PATH` already holds a marker (`cstudy doctor --fix` repairs a workspace); `PATH` is inside another workspace; `PATH` is at or below a content checkout (a directory with `problems/` and `schemas/`) unless `--force` |
| Files | Copies the template: the practice projects (`python/`, `typescript/`, `jvm/`, `go/`, `rust/`) and `go.work`, `notes/` and `problems/` (each with `.gitkeep`), `README.md` and `.gitignore`; makes `jvm/gradlew` executable; writes the marker. An existing file is never overwritten, so `cstudy init` can adopt a directory that already has files (for example a cloned repository) |
| Runtime | Materializes the runners into `.cs/runtime/` ([below](#runner-runtime)), so an IDE can import the projects right away |
| IDE files | Writes the [IDE files](#ide-files) of VS Code and IntelliJ IDEA, as `cstudy ide` does; `--ide vscode` or `--ide idea` (repeatable) writes only those, `--no-ide` none, and both together exit 3 |
| `--git` | Runs `git init` in `PATH`; `cstudy` never commits |
| Output | `created workspace <path>`, the number of files written and skipped, the IDE files line of [`cstudy ide`](cli.md#cstudy-ide), then the next steps: `cd <path>`, `cstudy doctor --fix`, `cstudy start two-sum` |

`cstudy init` installs nothing: `cstudy doctor --fix` runs `uv sync`, `pnpm install` and the Gradle warm-up. The Go and Rust toolchains are optional, although problems have Go and Rust references: neither command runs `go` or `cargo`, so a machine without them gets the same workspace, and only `--lang go` needs Go 1.24 or newer and `--lang rust` Rust 1.80 or newer (without them, `cstudy test` exits 4 with `go was not found on PATH` or `cargo was not found on PATH`). `cstudy doctor` checks `go`, `rustc` and `cargo` and only warns when one is missing or too old ([ADR 0012](../decisions/0012-go-and-rust.md)).

`rust/Cargo.toml` is for the editor: each problem file is an `[[example]]` with `crate-type = ["lib"]`, a crate of its own that rust-analyzer checks, with `autoexamples = false` so only listed files count and `cs_support`, `rust_decimal` and `chrono` as dev-dependencies; `rust/.cargo/config.toml` resolves crates.io from the runtime's vendored crates, so rust-analyzer needs no network. `cstudy start --lang rust` appends the problem's entry when the manifest has none for its name or file, and leaves a manifest that does not parse alone. `lib.rs` is empty: a package needs one target before the first problem starts. `cstudy` builds solutions elsewhere ([runners](runners.md#rust-build-details)), so an edit to the manifest never affects a run.

The workspace `.gitignore` ignores `/.cs/*` except `/.cs/workspace.toml` and `/.cs/ide.json`, `/.statements/`, `progress.db*`, `node_modules/`, `.venv/`, `build/`, `.gradle/`, `.kotlin/`, `target/`, `__pycache__/`, `.ruff_cache/`, and IntelliJ's per-user files (`.idea/workspace.xml`, `tasks.xml`, `usage.statistics.xml`, `dictionaries/`, `shelf/`, `libraries/`, `modules.xml`, `dataSources*`, `contentModel.xml`, `*.iml`). Practice files, notes, `.archive/`, your problems and the IDE files stay tracked, and you commit them when you choose ([PRD Q3](../prd.md#8-open-questions)).

## Runner runtime

The practice projects build and run against the runners, and Gradle, uv and Node write next to what they build. The bundled runners live in the installed package, which must stay read-only, so each workspace gets its own copy:

| Item | Rule |
|------|------|
| Location | `.cs/runtime/runners/{python,typescript,jvm,go,rust}`: the content root's `runners/<name>/` without `tests/` and build output |
| Stamp | `.cs/runtime/stamp.json`: a SHA-256 over the relative path and bytes of every copied source file |
| Refresh | Before the first runner prepares in a command, and in `cstudy doctor`, `cstudy doctor --fix` and `cstudy init`: when the stamp differs from the content's digest, changed files are rewritten, removed files deleted, unchanged files keep their timestamps, and build output (`build/`, `.gradle/`, `node_modules/`, `.kotlin/`, `target/`, `__pycache__/`) stays |
| Wiring | Relative paths in the tracked project files: `python/pyproject.toml` depends on `../.cs/runtime/runners/python` (editable), `typescript/support.ts` re-exports `../.cs/runtime/runners/typescript/support.ts`, `jvm/settings.gradle.kts` includes `../.cs/runtime/runners/jvm`, `go/go.mod` replaces the module `cstudy` (the runner and `cstudy/support`) with `../.cs/runtime/runners/go` and `github.com/shopspring/decimal` with its copy in `../.cs/runtime/runners/go/third_party`, `rust/Cargo.toml` takes `cs_support` from `../.cs/runtime/runners/rust/cs_support` and `rust/.cargo/config.toml` replaces crates.io with `../.cs/runtime/runners/rust/vendor`, and the reference build in `.cs/build/jvm` includes `../../runtime/runners/jvm` while `.cs/build/go/go.work` replaces `cstudy` with `../../runtime/runners/go` |
| IDE launcher | `.cs/runtime/ide/cstudy-launcher.jar`, a copy of the jar shipped in the package ([IDE files](#ide-files)); installed whenever the runtime is refreshed, even when the stamp matches, and by `cstudy ide`. A missing or different copy makes the runtime stale |

Because the wiring is relative, a workspace keeps working when it moves or is cloned on another machine; there `cstudy doctor --fix` recreates `.cs/runtime/` (with the launcher), the venv, `node_modules` and the Gradle build. Editors open the workspace root with its [IDE files](#ide-files), or each project on its own: `python/` (pyright and ruff find `.venv`), `typescript/` (tsserver finds `node_modules`), `jvm/` (IntelliJ imports it as one Gradle project), `go/` (gopls reads `go.mod`) and `rust/` (rust-analyzer reads `Cargo.toml`).

## IDE files

`cstudy init` and [`cstudy ide`](cli.md#cstudy-ide) write project files so that the workspace root opens in VS Code or IntelliJ IDEA with every `cstudy` action ready to run and debug ([ADR 0010](../decisions/0010-ide-integration.md)). `cstudy` stays the judge: the IDE runs `cstudy` commands, and debugging attaches to the runner that `cstudy test --debug` starts.

| Action | Current file (the solution in the editor is the target) | Active attempt (no target) |
|--------|-------------------------------|----------------|
| `test`, `test --perf`, `test --typecheck` (TypeScript), `bench`, `hint` | yes | yes |
| `done --rating=ok\|easy\|hard`, `done --gave-up` | yes | yes |
| `solution`, `show`, `start --no-open` | yes | no: the target is required |
| `test --debug` (VS Code), `test --debug --debug-connect` (IntelliJ, Java and Kotlin) | yes | yes |
| `next`, `stats`, `doctor` | workspace commands, no target | |

One catalog (`coding_study/domain/ide_actions.py`) lists these actions, and both IDEs' files are generated from it; the tests parse every command line with the real `cstudy` command line.

| File | Holds |
|------|-------|
| `.vscode/tasks.json` | A `process` task per action and scope (`cstudy test (current file)` runs `cstudy test ${file}` in `${workspaceFolder}`); `done` asks for the outcome through a `pickString` input. The `cstudy test --debug` tasks are background tasks whose problem matcher ends at `cstudy: waiting for debugger on 127.0.0.1:<port>` |
| `.vscode/launch.json` | `Debug current file (<language>)` and `Debug active attempt (<language>)` for Python (`debugpy` attach, port 5678), TypeScript (`node` attach, 9229), Java (`java` attach, 5005), Go (the Go extension's `go` attach in `"mode": "remote"` to the headless Delve, 2345) and Rust (CodeLLDB's `lldb` attach: `targetCreateCommands` `["target create \"\""]`, an empty target that takes the executable the debug server reports, since each run launches its own copy of the runner, then `processCreateCommands` `["gdb-remote 127.0.0.1:12345"]`; `preTerminateCommands` an lldb `script` one-liner that kills the process only while it is alive (`lldb.process.is_alive`; a plain `process kill` would print `error: Process must be launched.` after a run that already finished), because CodeLLDB detaches from an attached process when its session ends and the runner would go on without a debugger; and `sourceLanguages` `["rust"]` for Rust's formatters), each starting its `cstudy test --debug` task first; all on 127.0.0.1. None for Kotlin: VS Code's Java debugger never binds Kotlin breakpoints ([vscode-java-debug#241](https://github.com/microsoft/vscode-java-debug/issues/241)) |
| `.vscode/settings.json` | `python.defaultInterpreterPath` `${workspaceFolder}/python/.venv/bin/python`, `typescript.tsdk` `typescript/node_modules/typescript/lib`, `java.import.gradle.enabled`, `go.toolsEnvVars` `{"GOTOOLCHAIN": "local"}`, `rust-analyzer.linkedProjects` `["rust/Cargo.toml"]` with `rust-analyzer.check.allTargets` and `rust-analyzer.check.extraArgs` `["--keep-going"]`, watcher and search exclusions for build output (`target` included); no JDK path |
| `.vscode/extensions.json` | Recommends `ms-python.python`, `ms-python.debugpy`, `vscjava.vscode-java-pack`, `vscjava.vscode-gradle`, `golang.go`, `rust-lang.rust-analyzer`, `vadimcn.vscode-lldb` (CodeLLDB, the Rust debugger) |
| `.idea/misc.xml` | The project JDK `21` (`JavaSDK`, language level `JDK_21`): the toolchain of the practice projects |
| `.idea/gradle.xml` | `jvm/` linked as a Gradle project with its `java` and `kotlin` modules, run with the project JDK (`#USE_PROJECT_JDK`) |
| `.idea/runConfigurations/*.xml` | Shared run configurations in the folders `cstudy: current file` (JAR Application configurations that start the launcher with `"$FilePath$"`), `cstudy: active attempt` and `cstudy: workspace` (Shell Script configurations run in the terminal), and `cstudy: debug`: **Debug JVM (listen)**, a Remote JVM Debug configuration listening on port 5005 that restarts after each session, and the compounds `Debug current file (Java, Kotlin)` and `Debug active attempt (Java, Kotlin)`, each starting the listener and `cstudy test --debug --debug-connect`. Each file is named after its configuration as IntelliJ names it (`cstudy test (current file)` is `cstudy_test__current_file_.xml`) |

Go and Rust need no tasks or run configurations of their own: every action is language-agnostic, so `cstudy test (current file)` runs `cstudy test ${file}` on a `.go` or `.rs` solution as it does on a `.py` one, and IntelliJ writes no Go or Rust project files and no Go or Rust debug configurations: debug them in VS Code (above) or with any client of [debug mode](runners.md#debug-mode). The settings are what the two editors need to analyse the practice files:

| Setting | Why |
|---------|-----|
| `go.toolsEnvVars` `GOTOOLCHAIN=local` | The Go extension's tools (gopls) run as `cstudy` does and never download the toolchain `go/go.mod` asks for ([toolchains](../guides/toolchains.md#go)). gopls finds `go/` through the `go.work` at the workspace root; no setting is needed for that |
| `rust-analyzer.linkedProjects` `rust/Cargo.toml` | The Cargo project is in `rust/`, not at the workspace root |
| `rust-analyzer.check.allTargets`, `rust-analyzer.check.extraArgs` `--keep-going` | Each problem is an `[[example]]` built as a library crate ([ADR 0012](../decisions/0012-go-and-rust.md)); checking every target covers them, and `--keep-going` reports the errors of every problem when one is broken instead of stopping at the first |

An existing workspace gets the new settings and extensions from `cstudy ide`, which follows the rewriting rule below: it updates `settings.json` and `extensions.json` while they are as `cstudy` wrote them, and keeps (with a warning) the ones you edited until `cstudy ide --force`, or until you copy the keys over. `cstudy doctor --fix` never writes IDE files. Debug configurations for Go and Rust are not generated yet.

| Rule | Detail |
|------|--------|
| Launcher | IntelliJ expands macros such as `$FilePath$` in JAR Application configurations but not in Shell Script ones, so current-file configurations run `.cs/runtime/ide/cstudy-launcher.jar` ([runtime](#runner-runtime)). It runs `cstudy <arguments>` with the same standard streams and exits with its exit code; it finds `cstudy` through `-Dcstudy.executable`, `CSTUDY_EXECUTABLE`, `PATH`, `UV_TOOL_BIN_DIR`, `XDG_BIN_HOME` and `~/.local/bin`, and exits 127 naming `CSTUDY_EXECUTABLE` when it finds none. Built reproducibly from `tools/ide-launcher/` (javac 21, Java 17 bytecode) and shipped as package data; a test rebuilds it and compares the bytes |
| No editor focused | IntelliJ passes the project directory as `$FilePath$`; [a directory target](cli.md#solution-file-targets) exits 3 with `open a solution file in the editor first` |
| Manifest | `.cs/ide.json`: `{"format": 1, "files": {<path>: <SHA-256 of what cstudy wrote>}}`, sorted, tracked with the IDE files so a clone knows which files are still as cstudy wrote them |
| Rewriting | A missing file is written; a file still matching its recorded digest is overwritten; a file already holding the new content is left as it is (and recorded); any other file at a generated path, edited since or never written by cstudy, is kept with a warning until `cstudy ide --force`. Files cstudy does not generate are never touched |
| Removal | A recorded file this `cstudy` no longer generates is deleted while it matches its digest; once edited, it is kept and forgotten |
| Stable output | JSON with two-space indents in a fixed key order; XML from ElementTree in IntelliJ's layout; every file ends with a newline, so generating again changes no byte |

Not set from project files, because IDEs keep them per user or need a plugin: the JDK definition behind the name `21` (IntelliJ offers to set up the missing SDK), the first **Load Gradle Project** in IntelliJ, a Python SDK in IntelliJ (Python plugin), a JDK for VS Code's Java extension, Python and Node debugging in IntelliJ (Python plugin; Node attach is IntelliJ IDEA Ultimate only), and Kotlin debugging in VS Code. The workspace README lists them.

## cstudy doctor in a workspace

| Check | `ok` | Otherwise |
|-------|------|-----------|
| `content` | Path, `bundled` or `checkout` | FAIL when the content root cannot be found |
| `workspace` | Path and `created with cstudy <version>` (with the running version when it differs) | WARN when there is no workspace (`fix: cstudy init`); FAIL for an unreadable marker or a newer schema |
| `workspace files` | Every core template file exists (everything but the Go and Rust files below) | FAIL listing up to 5 missing files, `fix: cstudy doctor --fix` |
| `go and rust files` | `go.work` and the files of `go/` and `rust/` exist | WARN listing up to 5 missing files, `fix: cstudy doctor --fix`: a workspace created before Go and Rust existed lacks them, and nothing fails until you use `--lang go` or `--lang rust` |
| `runner runtime` | The stamp matches the content and the IDE launcher is the shipped one | FAIL when missing or stale, `fix: cstudy doctor --fix` |
| `jvm/gradlew`, `python/.venv`, `python debugpy`, `typescript/node_modules` and `runner <lang>` | As in [cli](cli.md#cstudy-doctor) | As in [cli](cli.md#cstudy-doctor) |

`cstudy doctor --fix` first writes every missing template file (never overwriting one, so practice files are never touched), refreshes the runner runtime, then runs `uv sync` in `python/`, `pnpm install` in `typescript/` (and in the content checkout's `runners/typescript` when the content is a checkout), and the Gradle warm-up in `jvm/`. Outside a workspace it exits 3.

## Your own problems

`<workspace>/problems/` uses the [problem format](problem-format.md) and is overlaid on the content root's `problems/`:

| Rule | Behavior |
|------|----------|
| Catalog | The union, in directory name (id) order; `cstudy list`, `cstudy next`, `cstudy start`, `cstudy test` and `cstudy verify` treat both alike |
| Slug collision | The workspace problem wins and hides the content problem with that slug entirely (no file-level merge). Your practice files and progress therefore always match the problem you wrote, also after an upgrade adds a problem with your slug |
| Id collision | Ids only order and name directories; two problems with the same id and different slugs are both listed, and `cstudy verify` reports the duplicate id (S2) |
| `cstudy new` | With bundled content it writes `problems/<id>-<slug>/` in the workspace, numbering from `5001` above the workspace's highest id, so new catalog problems never take your ids; with an editable checkout it writes into the checkout as before (highest checkout id plus one) |
| Tracks | Non-autograded items come from the content root only |

## Developing coding-study

The checkout is content, not a workspace:

- `cstudy init` inside it refuses without `--force`; as a second guard the root `.gitignore` ignores `.cs/`, `.statements/`, `progress.db*` and `progress-export.json` anywhere, and `/workspace/`, `/workspaces/`, `/ws/`, `/python/`, `/typescript/`, `/jvm/`, `/notes/` and `/.archive/` at the root.
- Point `CSTUDY_WORKSPACE` (or `--workspace`) at a workspace outside the checkout; `uv run cstudy verify` then reads the checkout's content and builds with that workspace's toolchains.
- The CLI tests never use a workspace in the checkout: fixtures create temporary workspaces, and the slow tests set one up per session with `cstudy init` and the `cstudy doctor --fix` steps.

## Replaces

`CS_ROOT` and the repository-root search (`problems/` and `schemas/` above the current directory) are gone: `CSTUDY_CONTENT` or `--content` picks content, and `CSTUDY_WORKSPACE` or `--workspace` picks the workspace.
