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
  .cs/                    # index, cases, calibration, build, runs caches, project manifests and locks (ignored)
  .gitignore, README.md
  .vscode/, .idea/        # IDE project files: tasks, run and debug configurations, SDK settings
  python/                 # pyproject.toml (dev tools: pyright, ruff, debugpy, pytest), uv.lock, practice/<snake_slug>.py
  typescript/             # package.json, pnpm-lock.yaml, tsconfig.json, support.ts, practice/<slug>.ts
  jvm/                    # Gradle wrapper, settings.gradle.kts, java/ and kotlin/ subprojects
  go/                     # go.mod (module workspace, Go 1.24), practice/<snake_slug>/<snake_slug>.go
  go.work                 # use ./go, so gopls and the go command find go/ from the root
  rust/                   # Cargo.toml (package practice, one [[example]] per started problem), .cargo/config.toml, lib.rs, practice/<snake_slug>.rs
  projects/               # one folder per started project problem: projects/<slug>/ (tracked)
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
| Files | Copies the template: the practice projects (`python/`, `typescript/`, `jvm/`, `go/`, `rust/`) and `go.work`, `notes/`, `problems/` and `projects/` (each with `.gitkeep`), `README.md` and `.gitignore`; makes `jvm/gradlew` executable; writes the marker. An existing file is never overwritten, so `cstudy init` can adopt a directory that already has files (for example a cloned repository) |
| Runtime | Materializes the runners into `.cs/runtime/` ([below](#runner-runtime)), so an IDE can import the projects right away |
| IDE files | Writes the [IDE files](#ide-files) of VS Code and IntelliJ IDEA, as `cstudy ide` does; `--ide vscode` or `--ide idea` (repeatable) writes only those, `--no-ide` none, and both together exit 3 |
| `--git` | Runs `git init` in `PATH`; `cstudy` never commits |
| Output | `created workspace <path>`, the number of files written and skipped, the IDE files line of [`cstudy ide`](cli.md#cstudy-ide), then the next steps: `cd <path>`, `cstudy doctor --fix`, `cstudy start two-sum` |

`cstudy init` installs nothing: `cstudy doctor --fix` runs `uv sync`, `pnpm install` and the Gradle warm-up. The Go and Rust toolchains are optional, although problems have Go and Rust references: neither command runs `go` or `cargo`, so a machine without them gets the same workspace, and only `--lang go` needs Go 1.24 or newer and `--lang rust` Rust 1.80 or newer (without them, `cstudy test` exits 4 with `go was not found on PATH` or `cargo was not found on PATH`). `cstudy doctor` checks `go`, `rustc` and `cargo` and only warns when one is missing or too old ([ADR 0012](../decisions/0012-go-and-rust.md)).

`rust/Cargo.toml` is for the editor: each problem file is an `[[example]]` with `crate-type = ["lib"]`, a crate of its own that rust-analyzer checks, with `autoexamples = false` so only listed files count and `cs_support`, `rust_decimal` and `chrono` as dev-dependencies; `rust/.cargo/config.toml` resolves crates.io from the runtime's vendored crates, so rust-analyzer needs no network. `cstudy start --lang rust` appends the problem's entry when the manifest has none for its name or file, and leaves a manifest that does not parse alone. `lib.rs` is empty: a package needs one target before the first problem starts. `cstudy` builds solutions elsewhere ([runners](runners.md#rust-build-details)), so an edit to the manifest never affects a run.

The workspace `.gitignore` ignores `/.cs/*` except `/.cs/workspace.toml` and `/.cs/ide.json`, `/.statements/`, `progress.db*`, `node_modules/`, `.venv/`, `build/`, `.gradle/`, `.kotlin/`, `target/`, `__pycache__/`, `.ruff_cache/`, `projects/*/.venv` and `projects/*/uv.lock` ([project folders](#project-folders): the `.venv` of a project is a symbolic link, which the pattern `.venv/` with its trailing slash does not match), `projects/*/go.work` and `projects/*/go.work.sum`, `projects/*/Cargo.lock`, which the native `cargo test` writes, and IntelliJ's per-user files (`.idea/workspace.xml`, `tasks.xml`, `usage.statistics.xml`, `dictionaries/`, `shelf/`, `libraries/`, `modules.xml`, `dataSources*`, `contentModel.xml`, `*.iml`). Practice files, project folders, notes, `.archive/`, your problems and the IDE files stay tracked, and you commit them when you choose ([PRD Q3](../prd.md#8-open-questions)).

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

## Project folders

A [project problem](problem-format.md#project-problems) is solved in `projects/<slug>/`: one self-contained folder per started project, which `cstudy start` fills from the problem's `starter/` tree and which you track like practice files ([ADR 0014](../decisions/0014-project-problems.md)). It opens as an editor root of its own. Nothing is installed per project: the folder reaches the workspace's toolchain installs by relative path, so a project starts offline (NFR-6), on the JVM once `cstudy doctor --fix` has cached the test libraries ([below](#jvm-project-folders)), and survives a move or a clone of the workspace.

| Item | Python | TypeScript |
|------|--------|------------|
| Toolchain | The workspace venv, through the relative symbolic link `projects/<slug>/.venv -> ../../python/.venv`, which `cstudy start` creates. A relative target survives moving and copying the workspace, where an absolute one would dangle. The workspace template's dev group lists pytest, next to debugpy, pyright and ruff | The workspace's Node and `typescript/node_modules`: `tsconfig.json` takes its types from `../../typescript/node_modules/@types` |
| Build files | The starter's `pyproject.toml`, tool tables only ([starter](problem-format.md#starter)): no `[project]` table, `requires-python` or `[tool.uv]`, because a `requires-python` above the venv's Python makes `uv run` delete the target of the `.venv` link, the shared `python/.venv`. Without a `[project]` table no second venv is created and no `uv.lock` is needed | The starter's `package.json` (`"type": "module"`, no dependencies) and `tsconfig.json` |
| Editors | pyright, basedpyright and Pylance resolve imports between the project's files, its `tests/` and subfolders, `pytest` and `cs_support`, through `[tool.pyright]` `venvPath = "."` and `venv = ".venv"`; ruff reads `[tool.ruff]` | tsserver reads `tsconfig.json`; VS Code uses the workspace's TypeScript (`typescript.tsdk`) |
| How `cstudy` runs it | `python/.venv/bin/python` by path, never the venv's console scripts, whose shebangs keep the venv's absolute path after the workspace moves. Every process it starts for a project gets `UV_NO_SYNC=1` and `PYTHONPYCACHEPREFIX=<workspace>/.cs/pycache`, so no bytecode lands in the folder; the runner keeps the project root off the front of `sys.path` ([project jobs](runners.md#project-jobs)) | `node` on the files, as for other TypeScript runs |
| Native command | `.venv/bin/pytest` in the folder (after a workspace move, once `python/.venv` is recreated), or `uv run --no-sync pytest`; a plain `uv run` there writes a `uv.lock` (ignored) and warns about `requires-python`. Not `python -m pytest` from the folder: it puts the folder first on `sys.path`, where a file such as `random.py` shadows the standard library | `node --test` in the folder |
| Caches | `-p no:cacheprovider` in the starter keeps `.pytest_cache` out; `__pycache__/` is ignored if a native run writes one | none |

A Go folder is a module of its own ([ADR 0014](../decisions/0014-project-problems.md#go-spike-k5)):

| Item | Go |
|------|----|
| Toolchain | The `go` on PATH, as for practice files. The starter's `go.mod` (`module <slug>`) reaches the vendored decimal module in the [runner runtime](#runner-runtime) through `replace ../../.cs/runtime/runners/go/third_party/...`, so the folder needs no `go.sum` and no network |
| `go.work` | `projects/<slug>/go.work`, holding `go 1.24` and `use .`, which `cstudy start` writes when it is missing. The go command and gopls look for a `go.work` from the folder upward, so this one keeps the workspace's root `go.work` from claiming the folder. The root `go.work` never lists a project folder: a `use` line there breaks every go command once `--fresh` archives the folder, and two folders with one module path fail together. The file is untracked, like a Python folder's `.venv` link |
| Editors | gopls resolves the folder's packages, its subpackages and the vendored module through its `go.work`, whether the editor opens the folder or the workspace root |
| How `cstudy` runs it | Binaries of its own in `.cs/build/go`, built against a `go.work` per project root there ([Go project jobs](runners.md#go-project-jobs)); the folder's own `go.work` is not used |
| Native command | `go test ./...` in the folder |
| Caches | none in the folder: the go command keeps its build cache per user |

| Rule | Detail |
|------|--------|
| Start | A new attempt copies `starter/` without overwriting a file; a resumed attempt copies it only when the folder is missing, writes back a missing generated test file of an unlocked level, and recreates a missing or dangling `.venv` link ([cli](cli.md#cstudy-start)) |
| Archive | `--fresh` and review attempts move the folder to `.archive/<slug>/<attempt_id>-<lang>/`, without the `.venv` link and caches, before copying the starter again. When that directory already exists, `cstudy start` exits 3 and moves nothing |
| Manifest | `.cs/projects/<slug>.json`, outside the folder and ignored like the rest of `.cs/`: every file `cstudy` provided in the folder, each starter file and the generated test file of each open level, with the SHA-256 of the content it provided, also where it kept a file of yours at that path. The document is `{"format": 1, "files": {<path>: {"origin": "starter" or "level", "level": <n>, "sha256": <digest>}}}`, sorted by path, with `level` for generated files only. A new attempt writes it anew from the starter; a generated test file is recorded when `cstudy` writes it, or keeps a file at its path that the manifest does not name yet; a resumed attempt keeps it, and writes it again from the starter when the folder or the manifest is missing (a folder you deleted, a clone). An archived folder takes none along. [`cstudy status`](cli.md#cstudy-status) compares the folder with it, so a starter file stays unchanged after a newer `cstudy` changes the starter |
| Lock | `.cs/projects/<slug>.lock`, an exclusive file lock that every command writing to a project takes, so two commands, or an interface racing the CLI, never interleave: `cstudy start` holds it for the whole start (a second `cstudy start` then resumes the attempt the first began), a submission that passed every case holds it while it opens the next level or records the full pass, and [`cstudy start --restore`](cli.md#restoring-a-file) while it writes the file back. Under the lock the submission reads the attempt again: of two submissions graded at once only one opens the level, and one graded while `cstudy start --fresh` replaced the attempt opens nothing. Grading and `cstudy test` run without it. A second command waits for it; the lock ends with its holder, however it ends |
| Watched and hashed | Every file under the folder except `.venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `build`, `.gradle`, `.kotlin` and `target`, and the folder's `uv.lock` and `Cargo.lock`: `cstudy test --watch` watches them and `code_hash` hashes their relative paths and bytes in path order. The workspace `.gitignore` already ignores `build/`, `.gradle/`, `.kotlin/` and `target/` wherever they appear, in project folders too |
| Go `go.work` | `cstudy start` writes the folder's `go.work` when it is missing, on a new and on a resumed attempt, and `cstudy doctor --fix` restores it; it is untracked, so `code_hash`, `--watch` and archives leave it out with `go.work.sum` |

### JVM project folders

A Java or Kotlin project folder is a Gradle build of its own, opened as an editor root of its own ([ADR 0014](../decisions/0014-project-problems.md#java-and-kotlin-spike-k4)).

| Item | Java and Kotlin |
|------|-----------------|
| Toolchain | The workspace's JDK 21, Gradle wrapper and daemon, and runner runtime. `settings.gradle.kts` finds the workspace by walking up to `.cs/workspace.toml`, takes `jvm/gradle/libs.versions.toml` as its version catalog and includes `.cs/runtime/runners/jvm`, whose `cs.project` plugin sets the JDK, JUnit, kotlin.test and the runner. No link is needed, and the same files build in a reference's copy under `.cs/build/projects/` |
| Build files | The starter's `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and `gradle/wrapper/gradle-wrapper.properties`, exactly as the template writes them ([starter](problem-format.md#starter)); the wrapper properties name the workspace's Gradle, so an IDE that opens the folder uses it |
| Editors | IntelliJ IDEA opens the folder as a Gradle project; VS Code's Java extension imports it with the settings the workspace already has (`java.import.gradle.enabled`) |
| How `cstudy` runs it | `jvm/gradlew -p projects/<slug> --offline csClasspath` (or `csMainClasspath` before grading) on the shared daemon, under an exclusive lock per project build, then `java` on a private copy of what it built ([JVM project builds](runners.md#jvm-project-builds)) |
| Native command | `../../jvm/gradlew test` in the folder, which runs JUnit through Gradle's own test task |
| Caches | `build/`, `.gradle/` (the configuration cache) and, for Kotlin, `.kotlin/`, all ignored |
| Offline | A project build runs with `--offline`. JUnit, kotlin-test and their dependencies (`apiguardian-api` among them) are not in the workspace's own build, so `cstudy doctor --fix` builds the warm-up projects `.cs/runtime/runners/jvm/project-warmup/java` and `project-warmup/kotlin` once online, project folders like any other with one test each, and every folder then builds offline. Until then a build exits 4 naming `cstudy doctor --fix` |

### Rust project folders

A Rust project folder is a crate of its own ([problem-format](problem-format.md#rust-projects)).

| Item | Rust |
|------|------|
| Toolchain | The workspace's `rustc` and `cargo`, and the runtime's vendored crates, which the folder's `.cargo/config.toml` names by the relative path `../../.cs/runtime/runners/rust/vendor`. `cstudy start` writes that file when the folder lacks it, on a new or a resumed attempt, and never changes one that exists |
| Build files | The starter's `Cargo.toml` and `.cargo/config.toml`. The folder is not a member of `rust/`: Cargo refuses a member outside the workspace root |
| Editors | rust-analyzer analyses a Cargo project that `rust-analyzer.linkedProjects` names, so [`cstudy ide`](#ide-files) adds `projects/<slug>/Cargo.toml` of each Rust folder to it |
| How `cstudy` runs it | It builds in `.cs/build/rust-projects/<slug>/` with the dev profile and a private `CARGO_HOME`, and writes nothing into the folder ([runners](runners.md#rust-projects)) |
| Native command | `cargo test` in the folder: it writes `target/` and `Cargo.lock` there, both ignored |
| Caches | `target/` |

## IDE files

`cstudy init` and [`cstudy ide`](cli.md#cstudy-ide) write project files so that the workspace root opens in VS Code or IntelliJ IDEA with every `cstudy` action ready to run and debug ([ADR 0010](../decisions/0010-ide-integration.md)). `cstudy` stays the judge: the IDE runs `cstudy` commands, and debugging attaches to the runner that `cstudy test --debug` starts.

| Action | Current file (the solution in the editor is the target) | Active attempt (no target) |
|--------|-------------------------------|----------------|
| `test`, `test --perf`, `test --typecheck` (TypeScript), `bench`, `hint` | yes | yes |
| `done --rating=ok\|easy\|hard`, `done --gave-up` | yes | yes |
| `submit`, `status` (project problems) | yes | yes |
| `solution`, `show`, `start --no-open` | yes | no: the target is required |
| `test --debug` (VS Code), `test --debug --debug-connect` (IntelliJ, Java and Kotlin) | yes | yes |
| `next`, `stats`, `doctor` | workspace commands, no target | |

One catalog (`coding_study/domain/ide_actions.py`) lists these actions, and both IDEs' files are generated from it; the tests parse every command line with the real `cstudy` command line.

| File | Holds |
|------|-------|
| `.vscode/tasks.json` | A `process` task per action and scope (`cstudy test (current file)` runs `cstudy test ${file}` in `${workspaceFolder}`); `done` asks for the outcome through a `pickString` input. The `cstudy test --debug` tasks are background tasks whose problem matcher ends at `cstudy: waiting for debugger on 127.0.0.1:<port>` |
| `.vscode/launch.json` | `Debug current file (<language>)` and `Debug active attempt (<language>)` for Python (`debugpy` attach, port 5678), TypeScript (`node` attach, 9229), Java (`java` attach, 5005), Go (the Go extension's `go` attach in `"mode": "remote"` to the headless Delve, 2345) and Rust (CodeLLDB's `lldb` attach: `targetCreateCommands` `["target create \"\""]`, an empty target that takes the executable the debug server reports, since each run launches its own copy of the runner, then `processCreateCommands` `["gdb-remote 127.0.0.1:12345"]`; `preTerminateCommands` an lldb `script` one-liner that kills the process only while it is alive (`lldb.process.is_alive`; a plain `process kill` would print `error: Process must be launched.` after a run that already finished), because CodeLLDB detaches from an attached process when its session ends and the runner would go on without a debugger; and `sourceLanguages` `["rust"]` for Rust's formatters), each starting its `cstudy test --debug` task first; all on 127.0.0.1. None for Kotlin: VS Code's Java debugger never binds Kotlin breakpoints ([vscode-java-debug#241](https://github.com/microsoft/vscode-java-debug/issues/241)) |
| `.vscode/settings.json` | `python.defaultInterpreterPath` `${workspaceFolder}/python/.venv/bin/python`, `typescript.tsdk` `typescript/node_modules/typescript/lib`, `java.import.gradle.enabled`, `go.toolsEnvVars` `{"GOTOOLCHAIN": "local"}`, `rust-analyzer.linkedProjects` `["rust/Cargo.toml"]`, then `projects/<slug>/Cargo.toml` of each [Rust project folder](#project-folders) in path order, with `rust-analyzer.check.allTargets` and `rust-analyzer.check.extraArgs` `["--keep-going"]`, watcher and search exclusions for build output (`target` included) and for `projects/*/.venv`, the links to the shared venv; no JDK path |
| `.vscode/extensions.json` | Recommends `ms-python.python`, `ms-python.debugpy`, `vscjava.vscode-java-pack`, `vscjava.vscode-gradle`, `golang.go`, `rust-lang.rust-analyzer`, `vadimcn.vscode-lldb` (CodeLLDB, the Rust debugger) |
| `.idea/misc.xml` | The project JDK `21` (`JavaSDK`, language level `JDK_21`): the toolchain of the practice projects |
| `.idea/gradle.xml` | `jvm/` linked as a Gradle project with its `java` and `kotlin` modules, run with the project JDK (`#USE_PROJECT_JDK`) |
| `.idea/runConfigurations/*.xml` | Shared run configurations in the folders `cstudy: current file` (JAR Application configurations that start the launcher with `"$FilePath$"`), `cstudy: active attempt` and `cstudy: workspace` (Shell Script configurations run in the terminal), and `cstudy: debug`: **Debug JVM (listen)**, a Remote JVM Debug configuration listening on port 5005 that restarts after each session, and the compounds `Debug current file (Java, Kotlin)` and `Debug active attempt (Java, Kotlin)`, each starting the listener and `cstudy test --debug --debug-connect`. Each file is named after its configuration as IntelliJ names it (`cstudy test (current file)` is `cstudy_test__current_file_.xml`) |

Go and Rust need no tasks or run configurations of their own: every action is language-agnostic, so `cstudy test (current file)` runs `cstudy test ${file}` on a `.go` or `.rs` solution as it does on a `.py` one, and IntelliJ writes no Go or Rust project files and no Go or Rust debug configurations: debug them in VS Code (above) or with any client of [debug mode](runners.md#debug-mode). The settings are what the two editors need to analyse the practice files:

| Setting | Why |
|---------|-----|
| `go.toolsEnvVars` `GOTOOLCHAIN=local` | The Go extension's tools (gopls) run as `cstudy` does and never download the toolchain `go/go.mod` asks for ([toolchains](../guides/toolchains.md#go)). gopls finds `go/` through the `go.work` at the workspace root; no setting is needed for that |
| `rust-analyzer.linkedProjects` `rust/Cargo.toml` | The Cargo project is in `rust/`, not at the workspace root |
| `rust-analyzer.linkedProjects` `projects/<slug>/Cargo.toml` | Each Rust project folder is a crate of its own, outside `rust/`; a folder is a Rust project when it holds a `Cargo.toml`. A project started after the last `cstudy ide` is missing until `cstudy ide` runs again, and `cstudy doctor` says so |
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
| `projects` | `projects/` exists | WARN, `fix: cstudy doctor --fix` (a workspace created before project problems lacks it) |
| `python pytest` | pytest is installed in `python/.venv` | WARN, `fix: uv add --dev pytest --directory python`: only Python project problems need it |
| `project links` | Every Python project folder's `.venv` is the relative link to `../../python/.venv` and resolves | WARN listing up to 5 folders whose link is missing or dangling; `cstudy doctor --fix` recreates them |
| `go projects` | Every Go project folder (`projects/<slug>` with a `go.mod`) has its `go.work`, every `replace` in its `go.mod` that names a directory (the vendored modules' copies) names one that exists, and no two folders declare one module path | WARN listing up to 5 problems: a missing `go.work` (`cstudy doctor --fix` writes it), a `replace` that does not resolve (fix: `cstudy start <slug> --restore go.mod`), or a module path shared with another folder (give each folder its own `module` line). `cstudy` itself still grades and tests such folders |
| `rust project config` | Every Rust project folder (one with a `Cargo.toml`) has a `.cargo/config.toml` whose replacement source for crates.io is a directory that exists, resolved from the folder | WARN listing up to 5 folders, `fix: cstudy doctor --fix`, which writes a missing file and refreshes the runtime; a file that names another directory is kept (`cstudy start <slug> --restore .cargo/config.toml` writes the starter's back) |
| `rust linked projects` | Every Rust project folder's `Cargo.toml` is in `rust-analyzer.linkedProjects` of `.vscode/settings.json`; no row without that file | WARN listing up to 5 folders, `fix: cstudy ide` |
| `java project libraries`, `kotlin project libraries` | The language's warm-up project built, and every library (jar) on the test runtime classpath it wrote still exists, so project folders build offline | WARN, `fix: cstudy doctor --fix` (online once): only Java and Kotlin project problems need them; nothing to check before `jvm/` exists |
| `python/.venv location` | The shebang of the venv's console scripts names this `python/.venv` | WARN when it names another path (the workspace moved): the console scripts no longer run, though `cstudy` does; `fix: rm -rf python/.venv && cstudy doctor --fix` |

`cstudy doctor --fix` first writes every missing template file (never overwriting one, so practice files are never touched), recreates missing or dangling `.venv` links in Python project folders, missing `go.work` files in Go project folders and missing `.cargo/config.toml` files in Rust project folders, refreshes the runner runtime, then runs `uv sync` in `python/`, `pnpm install` in `typescript/` (and in the content checkout's `runners/typescript` when the content is a checkout), and the Gradle warm-up in `jvm/`: the runtime classpath of both practice projects, which caches the runner's own libraries, then the two warm-up projects of [JVM project folders](#jvm-project-folders). Outside a workspace it exits 3.

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

- `cstudy init` inside it refuses without `--force`; as a second guard the root `.gitignore` ignores `.cs/`, `.statements/`, `progress.db*` and `progress-export.json` anywhere, and `/workspace/`, `/workspaces/`, `/ws/`, `/python/`, `/typescript/`, `/jvm/`, `/notes/`, `/projects/` and `/.archive/` at the root.
- Point `CSTUDY_WORKSPACE` (or `--workspace`) at a workspace outside the checkout; `uv run cstudy verify` then reads the checkout's content and builds with that workspace's toolchains.
- The CLI tests never use a workspace in the checkout: fixtures create temporary workspaces, and the slow tests set one up per session with `cstudy init` and the `cstudy doctor --fix` steps.

## Replaces

`CS_ROOT` and the repository-root search (`problems/` and `schemas/` above the current directory) are gone: `CSTUDY_CONTENT` or `--content` picks content, and `CSTUDY_WORKSPACE` or `--workspace` picks the workspace.
