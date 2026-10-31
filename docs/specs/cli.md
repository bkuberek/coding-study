# Spec: CLI (`cstudy`)

`cstudy` is the interface: in the terminal, and through the local page that [`cstudy serve`](#cstudy-serve) serves, which calls the same use cases and starts the same commands ([web-ui](web-ui.md)). It is installed as a tool with its content bundled, and every command runs against a content root (problems, tracks, runners, schemas) and a workspace (your practice projects, notes and progress); [installation-and-workspaces](installation-and-workspaces.md) defines how both are found. Paths `cstudy` prints for workspace files are relative to the workspace root.

## Command summary

| Command | Purpose | Phase |
|---------|---------|-------|
| [`cstudy init`](installation-and-workspaces.md#cstudy-init) | Create a workspace | W1 |
| [`cstudy doctor`](#cstudy-doctor) | Check and set up toolchains | 0 |
| [`cstudy ide`](#cstudy-ide) | Write or refresh the VS Code and IntelliJ project files | W1 |
| [`cstudy start`](#cstudy-start) | Create or reopen a stub, open the statement, begin an attempt | 0 |
| [`cstudy test`](#cstudy-test) | Run the user's code against the cases; for a project problem, its native tests | 0 |
| [`cstudy submit`](#cstudy-submit) | Grade a project problem and open its next level | 8 |
| [`cstudy status`](#cstudy-status) | Show where an attempt stands | 8 (every kind in 9) |
| [`cstudy history`](#cstudy-history) | Show a problem's attempts, runs and review schedule | 9 |
| [`cstudy serve`](#cstudy-serve) | Serve the local web UI | 9 |
| [`cstudy solution`](#cstudy-solution) | Show reference code with its explanation | 0 |
| [`cstudy verify`](#cstudy-verify) | Content quality gate | 0 |
| [`cstudy list`](#cstudy-list) | Browse problems with filters | 0 (status columns in 1) |
| [`cstudy show`](#cstudy-show) | Print the rendered statement | 0 |
| [`cstudy done`](#cstudy-done) | Finish an attempt and schedule review | 1 |
| [`cstudy next`](#cstudy-next) | Pick what to practice | 1 |
| [`cstudy hint`](#cstudy-hint) | Reveal the next hint | 1 |
| [`cstudy new`](#cstudy-new) | Scaffold a new problem | 1 |
| [`cstudy bench`](#cstudy-bench) | Complexity ladder and memory analysis | 2 |
| [`cstudy stats`](#cstudy-stats) | Progress summary | 7 |
| [`cstudy mock`](#cstudy-mock) | Timed mock interview | 7 |
| [`cstudy export`](#cstudy-export) | Back up progress as JSON | 7 |
| [`cstudy import`](#cstudy-import) | Restore an export into an empty `progress.db` | 7 |

`<file>` is a [solution file path](#solution-file-targets). Commands that take an optional `<slug>` default to the active attempt: the most recent attempt with status `in_progress`. If none exists, they exit 3. Every command but `cstudy init`, `cstudy doctor`, `cstudy list` and `cstudy show` needs a workspace and exits 3 without one, pointing at `cstudy init`. The [IDE files](installation-and-workspaces.md#ide-files) run these commands on the file in the editor or on the active attempt.

## Solution file targets

[`start`](#cstudy-start), [`test`](#cstudy-test), [`submit`](#cstudy-submit), [`status`](#cstudy-status), [`hint`](#cstudy-hint), [`solution`](#cstudy-solution), [`done`](#cstudy-done), [`show`](#cstudy-show), [`history`](#cstudy-history) and [`bench`](#cstudy-bench) take the problem as `<slug>` or as the path of one of your solution files, so an IDE can run any command on the file in its editor: `cstudy test python/practice/two_sum.py` is `cstudy test two-sum --lang python`.

| Rule | Detail |
|------|--------|
| Path or slug | An argument is a path when it contains `/` or `\`, or ends in `.py`, `.ts`, `.java` or `.kt`; anything else is a slug or an id, even when a file of that name exists. Relative paths resolve against the current directory, so an IDE passes the absolute path of the open file |
| Files | The files [`cstudy start`](#cstudy-start) writes ([layout](../architecture.md#repository-layout)): `python/practice/<snake_slug>.py`, `typescript/practice/<slug>.ts`, `jvm/<java\|kotlin>/src/main/<java\|kotlin>/practice/<snake_slug>/<File>.<java\|kt>`, `go/practice/<snake_slug>/<File>.go` and `rust/practice/<snake_slug>.rs`. On the JVM and in Go any source file directly in the problem's package counts, such as the declared class of a class-design problem or a helper class. For a [project problem](problem-format.md#project-problems), any file at any depth under `projects/<slug>/` counts (`projects/bank-project-python/bank/ledger.py`), except under `.venv`, `node_modules`, build output (`build`, `.gradle`, `.kotlin`) and caches |
| Problem | The slug is the problem whose file name the path carries (`two_sum` is `two-sum`), or, under `projects/`, the folder's name; a path that names no problem exits 3 |
| Language | The path's language is the language of the run; a project file's language is its problem's, whatever the file's extension. `--lang` may repeat it; naming another language exits 3 with both. `hint`, `done` and `show` have no `--lang`: they act on the problem, as with its slug |
| Not a solution file | A path outside the workspace, or inside it but not at one of those locations, exits 3 with `not a solution file in this workspace: <path>` |
| Directory | A directory exits 3 with `open a solution file in the editor first (got a directory: <path>)`: IntelliJ passes the project directory as the current file when no editor has focus |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success; all cases passed |
| 1 | Test or verify failures (including `timeout` and `tle`) |
| 2 | User code failed to build or load (compile error, import error, missing symbol) |
| 3 | Usage error (bad flags, unknown slug, no active attempt, not autograded) |
| 4 | Environment error (toolchain missing, runner did not start) |
| 5 | Content error (schema or static check failure in problem files) |
| 70 | Internal error (bug in `cstudy` or a runner protocol violation) |
| 130 | Interrupted |

## Global flags

| Flag | Effect |
|------|--------|
| `--json` | Machine-readable output, as an option of the command (`cstudy stats --json`, not `cstudy --json stats`): `stats`, [`test`](#json-output), [`submit`](#cstudy-submit), [`status`](#cstudy-status), [`history`](#cstudy-history), [`list`](#cstudy-list), [`next`](#cstudy-next) and [`doctor`](#cstudy-doctor) have it; `bench` and `verify` do not yet |
| `--events` | The run as a stream of JSON events instead of the report, as an option of the command: [`test`](#cstudy-test) on every autograded problem and [`submit`](#cstudy-submit) have it ([Event stream](#event-stream)) |
| `--version` | Print `cstudy <version>` (for example `cstudy 0.1.0`), read from the installed package metadata, and exit 0 ([versioning](versioning.md)) |
| `--no-color` | Plain output (also when `NO_COLOR` is set or stdout is not a TTY) |
| `-v`, `--verbose` | Planned, not implemented yet: show runner commands, build output and timings |
| `--workspace PATH` | The workspace, before the command (`cstudy --workspace ~/ws start two-sum`); overrides `CSTUDY_WORKSPACE` |
| `--content PATH` | The content root, before the command; overrides `CSTUDY_CONTENT`. Unrelated to `cstudy list --content`, which filters by content status |

## Configuration

One user-level file: `$XDG_CONFIG_HOME/coding-study/config.toml` (default `~/.config/coding-study/config.toml`); `CSTUDY_CONFIG` overrides the path. All keys are optional; defaults below. Precedence everywhere: CLI flag, then this file, then the problem's `meta.yaml`, then built-in defaults.

```toml
default_lang = "python"          # python | typescript | java | kotlin | go | rust
open_on_start = true             # run $VISUAL or $EDITOR on cstudy start
progress_db = "progress.db"      # relative to the workspace root

[next]
tracks = ["dsa"]

[time_limit]
enabled = false                  # time limits are off unless enabled here or by flag
# value = "5x"                   # unset by default, so meta.yaml perf.time_limit applies
floor_ms = 100

[hang_guard]
# ms = 10000                     # unset by default, so case and meta.yaml values apply, then 10000

[bench]
reps = 7
memory = true

[schedule]
penalize_suboptimal = true
max_interval_days = 180

[done]
auto_commit = false              # reserved (PRD Q3)

[study_guides]
# root = "~/study-guides"        # unset by default: no study-guide links; absolute or "~/" path
```

`study_guides.root` is the directory that item `references.study_guides` paths are relative to ([study guides](content.md#study-guides)).

## cstudy doctor

```text
cstudy doctor [--fix | --json]
```

Checks Python 3.13, uv, Node 24 or newer, pnpm, JDK 21, Homebrew Gradle, Go 1.24 or newer, `rustc` 1.80 or newer and `cargo` (the Go and Rust toolchains are optional, so these three rows WARN, never FAIL, with a link to the [toolchains guide](../guides/toolchains.md)), Delve (`dlv`, found as [debug mode](runners.md#debug-mode) finds it; the row shows its version, and a release other than the tested 1.27.2 passes with `(cstudy is tested with 1.27.2)`) and Rust's debug server (`debugserver` on macOS, `lldb-server` on Linux; the row shows its path), which only `cstudy test --debug` needs, so they WARN too, with the install step and the guide (``needed for --debug with --lang go, run `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`: <guide>#go``), the config file, the content root, the workspace (core template files FAIL when missing, the optional `go.work`, `go/` and `rust/` files WARN; [workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)), the progress database (its schema against the one this `cstudy` migrates to: WARN when older, FAIL when newer), the Gradle wrapper, the workspace venv, `debugpy` and `pytest` in it, the `.venv` links of the Python project folders, the `go.work`, `replace` lines and module paths of the Go project folders, the `.cargo/config.toml` and rust-analyzer link of the Rust ones, the libraries that Java and Kotlin project folders build with offline ([workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)), `node_modules`, and that the runner of each core language (`python`, `typescript`, `java`, `kotlin`; the Go and Rust runners are not handshaken, since that would compile them) answers `hello`: the runner is prepared for a problem with no files (`cs-doctor-handshake`, so the JVM build compiles no practice code) and started with no jobs. Outside a workspace only the toolchains, the config and the content are checked. `--fix` first writes every missing workspace template file (never overwriting one), refreshes the runner runtime and migrates an older `progress.db` to the latest schema (one line, `migrated progress.db from schema 4 to 5`), then runs, in each workspace project that exists, `uv sync` in `python` (followed, when the venv cannot import pytest, by `uv add --dev --offline "pytest>=9.1"`, retried without `--offline` when it fails, so a workspace created before the template listed pytest gets it; when both fail the line is `FAIL` with `fix: once online, run: uv add --dev "pytest>=9.1" --directory python`), `pnpm install` in `typescript` (and, when the content is a checkout, in its `runners/typescript` for the runner's own `tsc` and Node types), and in `jvm`, unless `java -version` fails (then one `FAIL` line, `skipped: java is not installed or does not run`, with the JDK fix, replaces the Gradle steps), the Gradle warm-up: `./gradlew :java:csClasspath :kotlin:csClasspath -Pcs.only=cs_doctor_handshake` (builds the runner and support classes, resolves the runtime classpath so that the runner's own libraries are cached for offline builds, and warms the daemon without compiling practice files), then `./gradlew -p ../.cs/runtime/runners/jvm/project-warmup/java -q --console=plain csClasspath` and the same for `kotlin` (the warm-up projects, which cache what Java and Kotlin project folders build with: [JVM project folders](installation-and-workspaces.md#jvm-project-folders)), printing one line per command and the last 10 output lines of a failed one. `--fix` outside a workspace exits 3.

| Status | Meaning |
|--------|---------|
| `ok` | Check passed |
| `WARN` | Not blocking: Homebrew Gradle missing (only needed to regenerate the wrapper), no workspace yet, a workspace project not set up yet, or `debugpy` missing from an existing venv (only [`cstudy test --debug`](#cstudy-test) needs it; `fix: uv add --dev debugpy --directory python`, which also covers a workspace created before the template listed it); `pytest` missing from it (only Python project problems need it; `fix: cstudy doctor --fix` adds it); a `progress.db` of an older schema (it migrates on the next command that opens it, `--fix` migrates it now); no `projects/` folder; a dangling `.venv` link in a project folder, a `python/.venv` that moved, or Java or Kotlin project libraries not cached yet (all under [workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)); Go, Rust, Delve or Rust's debug server missing (only `--lang go`, `--lang rust` or their `--debug` needs them); a Delve that refuses the installed Go (Delve 1.27 or newer needs Go 1.25 or newer, so `--debug` with `--lang go` would fail) |
| `FAIL` | Blocks practice; a `fix:` hint follows when one applies. A `progress.db` of a newer schema than this `cstudy` reads fails too (`fix: upgrade cstudy`) |

```text
ok    python 3.13.2
ok    uv 0.10.11
ok    node v24.18.0 (type stripping)
ok    pnpm 9.15.9
ok    java 21.0.2
ok    content /home/me/.local/share/uv/tools/coding-study/lib/python3.13/site-packages/coding_study/content (bundled)
ok    workspace /home/me/ws (created with cstudy 0.1.0)
FAIL  python/.venv missing    fix: cstudy doctor --fix
ok    runner python answers hello: python 3.13.2, protocol 1
ok    runner kotlin answers hello: jvm 21.0.2, protocol 1
```

Exit 0 when no check reports `FAIL` (and, with `--fix`, every setup command succeeded), else 4.

`--json` prints the same checks as one document instead of the rows, and exits as the rows would; with `--fix` it is a usage error (`--json excludes --fix`, exit 3). Each check is one row: `name` (`python`, `workspace`, `runner kotlin`), `status` (`ok`, `warn` or `fail`), `detail` (the rest of the row, such as `3.13.2`, or `""` for a row with nothing after its name) and `fix` (the hint, or null). Progress notices, such as the Gradle warm-up, go to standard error. The page [`cstudy serve`](#cstudy-serve) serves shows it ([web-ui](web-ui.md#health-view)).

```json
{"workspace": "/home/me/ws", "passed": false, "checks": [
  {"name": "python", "status": "ok", "detail": "3.13.2", "fix": null},
  {"name": "python/.venv", "status": "fail", "detail": "missing", "fix": "cstudy doctor --fix"}
]}
```

`workspace` is the workspace's path, or null outside a workspace; `passed` is false when a check failed.

The `web ui assets` and `web server` rows check what `cstudy serve` needs ([installation-and-workspaces](installation-and-workspaces.md#web-ui-assets)). Both WARN, never FAIL, since practice in the terminal does not need them:

```text
ok    web ui assets 0.8 MB, digest matches
ok    web server starlette 1.10.0, uvicorn 0.54.0
```

## cstudy ide

```text
cstudy ide [vscode|idea|all] [--force]
```

Writes or refreshes the workspace's [IDE files](installation-and-workspaces.md#ide-files) (`.vscode/`, `.idea/`) for the named IDE (default: `all`), and installs the IntelliJ launcher into `.cs/runtime/ide/`. VS Code's `rust-analyzer.linkedProjects` lists the Rust project folders that exist when it runs; [`cstudy start`](#cstudy-start) refreshes VS Code's files the same way when it writes a new Rust project folder in a workspace whose VS Code settings `cstudy` wrote. `cstudy init` does the same unless `--no-ide`; `--ide vscode` or `--ide idea` (repeatable) limits it to those.

| Rule | Detail |
|------|--------|
| Rewrites | Only files that are missing or still as cstudy wrote them, by the digests in `.cs/ide.json`; a file you edited, or one at a generated path that cstudy never wrote, is kept and named in a warning |
| `--force` | Overwrites kept files too; files cstudy does not generate, such as a run configuration of your own, are never touched |
| Removed | A file an older `cstudy` generated and this one no longer does is deleted while unchanged |
| Output | `ide      vscode, idea · 3 created · 1 updated · 1 kept`, or `no changes`, then `warning  kept <path>: edited, or not written by cstudy (cstudy ide --force overwrites it)` per kept file |

Exit 0, also when files are kept; 3 outside a workspace or for another IDE name.

```text
ide      vscode, idea · 1 updated · 1 kept
warning  kept .vscode/tasks.json: edited, or not written by cstudy (cstudy ide --force overwrites it)
```

## cstudy start

```text
cstudy start <slug|file> [--lang L] [--fresh] [--timer DURATION] [--no-open] [--restore PATH]
```

| Flag | Effect |
|------|--------|
| `--lang` | Language; default `default_lang` |
| `--fresh` | Archive the existing file and write a new stub (implied for review attempts) |
| `--timer` | Time box, for example `25m` or `1h`; shown by `cstudy test`; finishing over time caps the grade at `hard` |
| `--no-open` | Do not launch the editor |
| `--restore` | Project problems: write one file of the folder back as `cstudy` provides it, and do nothing else ([below](#restoring-a-file)) |

Effects: generate or keep the stub ([runners](runners.md#stub-generation)), render `.statements/<slug>.md`, insert an attempt (`in_progress`), and open `$EDITOR <stub> <statement>`. Starting a problem that already has an `in_progress` attempt in the same language resumes it. A progressive problem's new attempt opens level 1, and the statement shows only the unlocked levels; the output adds a `level` line (`level      1 of 4: Set and get`).

```text
two-sum · easy · arrays-hashing · kotlin
stub       jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt
statement  .statements/two-sum.md
next       cstudy test --watch
```

A [project problem](problem-format.md#project-problems) starts in its one language: `--lang` may repeat it, another language exits 3 (`bank-project-python is solved in python only`), and `default_lang` never applies. A new attempt copies the problem's `starter/` tree to `projects/<slug>/`, never overwriting a file, links the folder to the workspace's toolchain (Python: [project folders](installation-and-workspaces.md#project-folders)), writes level 1's [test file](problem-format.md#generated-test-files), renders the statement at level 1, and opens `$EDITOR projects/<slug> <statement>`. A resumed attempt copies the starter only when the folder is missing, writes back a missing generated test file of an unlocked level, and recreates a missing or dangling `.venv` link; it never restores a file you deleted or changed (`--restore` does, one file at a time). `--fresh` and review attempts first move the folder to `.archive/<slug>/<attempt_id>-<lang>/`, without its `.venv` link and caches. `--timer` works as for every problem. The `project` line counts the files the folder holds, as `code_hash` sees them ([project folders](installation-and-workspaces.md#project-folders)): the starter's, the generated test files and your own, without the `.venv` link, `node_modules` and caches.

A start that writes a new Rust project folder, in a workspace where `cstudy` wrote `.vscode/settings.json` (`cstudy init` or `cstudy ide`, as `.cs/ide.json` records), then refreshes VS Code's files as `cstudy ide vscode` does, under the same [rewriting rule](installation-and-workspaces.md#ide-files), so `rust-analyzer.linkedProjects` names the folder. When that changed a file, the output adds the `ide` line of [`cstudy ide`](#cstudy-ide) before `next` (`ide        vscode · 1 updated`), and its warning when it kept a `settings.json` you edited. Without that recorded file it writes no IDE file, and a resumed attempt leaves them alone.

```text
bank-project-python · hard · practical · python · project
project    projects/bank-project-python (6 files)
entry      bank/bank.py: Bank
tests      tests/test_level_1.py (2 tests)
statement  .statements/bank-project-python.md
level      1 of 4: Accounts and transfers
next       cstudy test --watch, then cstudy submit
```

For non-autograded items (system design, code review) `cstudy start` copies the item's `template.md`, under a header comment, to `notes/<track>/<slug>.md`, renders `prompt.md` (plus the change under review) to `.statements/<slug>.md`, inserts an attempt with no language and opens both files. `--lang` is a usage error; `--fresh` and review attempts archive the notes to `.archive/<slug>/<attempt_id>-notes/`; `--timer` is recorded but does not cap the grade. When [`study_guides.root`](#configuration) is set, the statement ends with a `## Study guides` section and the output adds a `guide` line, after `prompt`, for each referenced guide whose file exists under the root (`guide      file:///home/me/study-guides/distributed-systems-study-guide.md#databases`).

```text
url-shortener · medium · system-design · 45 min
notes      notes/system-design/url-shortener.md
prompt     .statements/url-shortener.md
next       answer in the notes, then cstudy solution url-shortener
```

#### Restoring a file

`cstudy start <slug|file> --restore PATH` writes one file of a project folder back as `cstudy` provides it: a starter file, or the [generated test file](problem-format.md#generated-test-files) of an open level. It acts on the attempt in progress and starts, resumes and opens nothing.

| Rule | Detail |
|------|--------|
| `PATH` | Relative to the project folder, as `cstudy status --json` lists it (`bank/bank.py`, `tests/test_level_2.py`). `.` and `..` segments are resolved first (`bank/../bank/bank.py` is `bank/bank.py`); an absolute path, a `\` separator, a path that leaves the folder or names the folder itself exits 3 (`cannot restore ../progress.db: leaves the folder`) |
| Which files | Those the folder's [manifest](installation-and-workspaces.md#project-folders) records, deleted or not. A file of yours, or the test file of a locked level, exits 3: `cannot restore bank/ledger.py: not a starter file or a generated test file of an open level of bank-project-python` |
| Content | A starter file as the problem's `starter/` holds it now; a generated test file as `cstudy` generates it now. The manifest then records that content, so the file shows `unchanged` in `cstudy status`. A starter file the problem no longer has exits 3 |
| Links | Never written through: when the file, or a directory between the folder and it, is a symbolic link, `cstudy start` exits 3 (`cannot restore bank/bank.py: bank is a symbolic link`) and writes nothing; so does a directory at the file's path |
| Refusals (exit 3) | Another kind of problem (`--restore is for project problems`), no attempt in progress, a missing folder (`cstudy start <slug>` copies the starter again), `--fresh` or `--timer` with it (`--restore excludes --fresh and --timer`) |
| Lock | Held while it writes the file and the manifest ([project folders](installation-and-workspaces.md#project-folders)) |

```text
$ cstudy start bank-project-python --restore tests/test_level_2.py
bank-project-python · hard · practical · python · project
restored   tests/test_level_2.py (level 2 tests)
```

## cstudy test

```text
cstudy test [<slug|file>] [--lang L] [--watch] [--case ID]... [--all] [--level N]
        [--time-limit[=VALUE] | --no-time-limit] [--perf] [--typecheck] [--stress N] [--seed S]
        [--json | --events] [--debug [--debug-port N] [--debug-connect]]
```

| Flag | Effect |
|------|--------|
| `--watch` | Re-run on save of the user file (JVM: the problem's package directory), 150 ms debounce, screen cleared each run |
| `--case` | Run only these case ids |
| `--all` | Print every case, including passing hidden ones |
| `--level` | Progressive and project problems: run levels 1 to N; N above the unlocked level exits 3 (`level 3 is locked; pass level 2 with cstudy test first`), as does `--level` on a problem without levels |
| `--time-limit[=VALUE]` | Enable time limits; optional VALUE `5x` or `1500ms` ([precedence](performance-analysis.md#precedence)). The value only follows `=`: in `cstudy test --time-limit two-sum`, `two-sum` is the slug |
| `--no-time-limit` | Disable time limits even if config enables them; together with `--time-limit` it is a usage error |
| `--perf` | After all cases pass (not with `--case`), run a short bench (`reps` 3, stored in `bench_runs`) and print its verdict line and warnings; a wrong answer on a bench input prints `FAIL      wrong answer at n=...` and exits 1 |
| `--typecheck` | TypeScript: also run `pnpm exec tsc --noEmit` (type stripping does not type-check) |
| `--stress N` | 1 to 100. Concurrent problems: run every stress case N times per variant instead of `concurrency.runs` (default 3). Function and design problems: also run N [oracle inputs](#oracle-inputs), generated inputs checked against the oracle approach; progressive and project problems, and problems without `generator.py` or a Python oracle, exit 3 |
| `--seed S` | Concurrent problems: base seed of every selected stress case instead of its `seed`; run `r` uses `S + r`. In the `async` model this reproduces a reported failing run exactly (`--case s1 --seed 1007 --stress 1`). Other problems: the first oracle input's seed (default 1), so `--stress 1 --seed 17` reruns `oracle-17`; without `--stress` it exits 3 |
| `--json` | One [JSON document](#json-output) on standard output instead of the report; with `--watch` or `--debug` it is a usage error. With `--perf` the document's `perf` holds the check's verdict |
| `--events` | The run as an [event stream](#event-stream) instead of the report, on every autograded problem |
| `--debug` | Start the runner under the language's debug agent and wait for an IDE to attach to it, with every time limit off ([Debugging](#debugging)) |
| `--debug-port N` | With `--debug`: the agent's port, 1 to 65535. Defaults: Python 5678, TypeScript 9229, Java and Kotlin 5005, Go 2345, Rust 12345 |
| `--debug-connect` | With `--debug`, Java and Kotlin only: connect to an IDE that is already listening on the port instead of listening for it |

Output rules: visible cases are always listed; passing hidden cases collapse into a count unless `--all`; failing hidden cases show input, expected and actual (PRD Q10); a `TLE` line shows the measured time, the limit and its basis instead. Statuses: `PASS`, `FAIL`, `ERROR`, `TIMEOUT` (hang guard), `TLE` (time limit), `INVALID` (output not serializable as the declared type), `STALLED` (concurrent stress run still unfinished at its deadline), `NOT RUN`.

```text
$ cstudy test --time-limit
two-sum · kotlin · 14 cases (2 visible, 11 hidden, 1 generated) · time limit 5x · timer 12:31 / 25:00
build  1.8s (gradle, warm)

PASS     ex1   0.04ms
PASS     ex2   0.03ms
FAIL     h3    hidden
         input     nums=[-3, 8, 0, 3]  target=0
         expected  [0, 3]  (unordered)
         actual    [3, 3]
TLE      g1    hidden · 412ms > limit 95ms (5x hash-map, calibrated)
PASS     10 hidden cases

12/14 passed · 1 failed · 1 tle · total 2.6s
```

On a full pass the summary adds `all passed. Next: cstudy done --rating easy|ok|hard`. Every run is stored in `test_runs`, except a [debug run](#debugging). Exit codes: 0, 1, 2, 3, 4.

#### Concurrent problems

Sequential cases print as above. Each stress case prints one line per variant with its run count; a failure lists up to 3 failing runs with seed and reason ([verdict rules](problem-format.md#evaluating-a-run-and-a-case)). Stress cases are hidden, but always printed, because their scenario is the point of the exercise. `--time-limit` applies to sequential cases only.

```text
$ cstudy test bounded-blocking-queue --lang java
bounded-blocking-queue · java · 6 sequential (2 visible, 4 hidden) · 2 stress × 2 variants × 3 runs
build  1.6s (gradle, warm)

PASS     ex1   0.05ms
PASS     ex2   0.04ms
PASS     4 hidden cases
PASS     s1    platform · 3/3 runs · median 38ms
FAIL     s1    virtual · 1/3 runs passed
         run 0 · seed 1000  equal_multisets put.arg0 vs take: 2 missing (1000017, 3000431), 0 extra
         run 2 · seed 1002  distinct take: 2000005 (2 times)
STALLED  s2    platform · 0/3 runs passed · deadline 5000ms
         run 0 · seed 2000  producer[0] in put (op 704 of 1000) · consumer[0..2] in take
PASS     s2    virtual · 3/3 runs · median 61ms

8/10 passed · 1 failed · 1 stalled · total 4.9s
```

A failing run shows its first reason on the run line and up to 2 more below it. The header counts variants and runs in the singular when there is one (`2 stress × 1 variant × 3 runs`).

A pass is evidence, not proof: the summary of a concurrent problem adds `stress runs found no race (not a proof of thread safety)`. In `test_runs`, each (stress case, variant) counts as one case; `STALLED` counts in `timed_out`, `INVALID` in `errored`. With `--json`, each (stress case, variant) is `{"id", "variant", "status", "runs", "runs_passed", "median_ms", "failures": [{"run", "seed", "status", "reasons"}]}`.


Progressive problems ([problem-format](problem-format.md#progressive-problems)) run the cases of levels 1 to the unlocked level, and the header names them (`level 1 of 3`, `levels 1-2 of 3`). A run that passes every case of the unlocked level unlocks the next one and rewrites the statement; only the last level's pass prints the `cstudy done` hint:

```text
$ cstudy test
level-store · python · level 1 of 3 · 4 cases (1 visible, 3 hidden, 0 generated)

PASS     ex1   0.02ms
PASS     3 hidden cases

4/4 passed · total 0.3s
level 1 passed · unlocked level 2 of 3: Remove and size
statement  .statements/level-store.md (updated)
```

#### Project problems

On a [project problem](problem-format.md#project-problems), `cstudy test` runs the project's native suite through the runner ([suite job](runners.md#suite-job)): the generated test files of levels 1 to the unlocked level, the starter's test files and your own. It is feedback. The run is stored in `test_runs`, but it grades nothing and never opens a level: [`cstudy submit`](#cstudy-submit) does both.

| Flag | For a project problem |
|------|-----------------------|
| `--level N` | Runs the generated files of levels 1 to N and every other test file; N above the unlocked level exits 3, as for progressive problems |
| `--case ID` | A test id as the report prints it (`tests/test_level_1.py::test_ex1`), or its last part (`test_ex1`); repeatable. When no discovered test matches, the run prints `no test matches --case <ID>` and exits 3 |
| `--watch` | Re-runs on a change to any file under `projects/<slug>/` except `.venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `build`, `.gradle` and `.kotlin` |
| `--typecheck` | TypeScript: first runs the workspace's `tsc --noEmit -p projects/<slug>`. A folder that type-checks runs its suite as usual. A type error prints `BUILD FAILED` and every line `tsc` printed in place of the tests, runs no test, exits 2, and is stored as a run without tests; each error is a [diagnostic](#diagnostics) with source `typecheck`. A language without a type check (Python) runs its suite as usual |
| `--json`, `--debug`, `--debug-port`, `--no-time-limit` | As for every problem; `--debug` stops at breakpoints in the project's code and in its tests. Go debugs one package's tests: those of the `--case` tests, else the package of the generated test files ([Go project jobs](runners.md#go-project-jobs)). In Rust each test is a process of its own, so `--debug` runs one: the first that `--case` selects, or the first of the suite, and the report says that the others did not run ([Rust projects](runners.md#rust-projects)) |
| `--events` | The run as an [event stream](#event-stream) instead of the report: `test_start` and `test_result` per test |
| `--all` | Accepted and changes nothing: every test is listed |
| `--perf`, `--stress`, `--seed`, `--time-limit`, `--debug-connect` | Exit 3: `--perf is not available for project problems` |

```text
$ cstudy test
bank-project-python · python · levels 1-2 of 4 · timer 31:40 / 90:00
suite  pytest, 0.3s

PASS     tests/test_level_1.py::test_ex1
PASS     tests/test_level_1.py::test_ex2
FAIL     tests/test_level_2.py::test_ex3
         assert ['dan(300)', 'eve(350)'] == ['eve(350)', 'dan(300)']
PASS     tests/test_overdraft.py::test_refuses_overdraft   yours

3/4 passed · total 0.7s
```

| Rule | Detail |
|------|--------|
| Statuses | `PASS`, `FAIL` (an assertion failed: the framework's message, then `expected` and `actual` when it reports them), `ERROR` (another exception, a setup failure, or a test file that does not import), `SKIP`, `TIMEOUT`, `NOT RUN` |
| Origin | A test in a generated file of an unlocked level is untagged; a test in a file the problem's `starter/` holds is tagged `starter`, any other `yours`. In Rust a source file also holds unit tests, so only a starter file that declares a test (`#[test]`) in `starter/` holds starter tests, and a unit test's file comes from its module path ([Rust projects](runners.md#rust-projects)): a test you add to a starter module that came without tests is `yours` |
| Summary | Skipped tests are left out of the count. On a full pass: `all passed. Next: cstudy submit`; once a submission passed every case of every level (`first_pass_at`), `all passed · every level done. Next: cstudy done --rating easy\|ok\|hard`, as `cstudy submit` printed it. A run of some tests only (`--case`, or `--level` below the unlocked level) says `all selected tests passed` instead |
| Java and Kotlin | The folder's Gradle build compiles the main and test sources first ([JVM project builds](runners.md#jvm-project-builds)); code that does not compile ends the run as the suite's load error, listing the compiler's lines (at most 40) |
| Exit codes | 0 when every test that ran passed; 1 when one failed, errored, timed out or did not run, or when no test ran (`no tests ran`); 2 when code in the folder did not type-check, build or load, as for a single file: whenever the run has a [diagnostic](#diagnostics), which is when `--typecheck` found a type error, the suite could not run (a Java or Kotlin project that does not compile, a `conftest.py` that does not import), or a test file, Go package or Rust test target never ran its tests because it did not import or compile, even when other tests ran; a test that raises while it runs is a test result, not a diagnostic; 3; 4 (pytest missing from `python/.venv`: `fix: uv add --dev pytest --directory python`; `go` missing for a Go project; JVM project libraries not cached: `cstudy doctor --fix`) |
| `test_runs` | `total` counts every reported test but skipped ones; `failed` the `FAIL`s; `errored` the `ERROR`s and crashes; `timed_out` the `TIMEOUT`s; `tle` 0. `code_hash` covers the folder ([progress-and-scheduling](progress-and-scheduling.md#project-attempts)) |
| `--json` | The document below with `comparator` null, `oracle` null and `stress` empty, `diagnostics`, the run's [diagnostics](#diagnostics) (empty when the code loaded), after `load_error`, and `stopped_early` after `cases`: why the tests not reported never ran, such as `the runner was restarted 3 times`, or null when the suite ran to its end; `levels` as for progressive problems with `newly_unlocked` always false; each entry of `cases` is a test: `id`, `status` (`pass`, `fail`, `error`, `skip`, `timeout`, `not_run`), `duration_ns`, `origin` (`level`, `starter` or `yours`), `level` (the level of a generated file, else null), and `message`, `expected`, `actual`, `error` and `stdout` when set |

#### Oracle inputs

`cstudy test --stress N` on a function or design problem adds N inputs from `generator.py`, the same ones `cstudy verify --oracle` uses ([D4](authoring.md#what-cstudy-verify-checks)): input `oracle-<s>` uses seed `s` and a size drawn from 1 to 30 by that seed, for `s` from `--seed` (default 1). Their expected values are the outputs of the `oracle: true` approach's Python reference, computed once and cached in `.cs/cases/`, whatever language the attempt is in; the comparator judges them like any case. Time limits do not apply to them. They count in the summary and the exit code, but, like the `--perf` check, not in `test_runs`: the stored run, `first_pass_at` and the rating rule of `cstudy done` cover the problem's own cases, so a failing oracle input exits 1 without turning a passing solution into a failed attempt.

The report shows at most 3 failing oracle inputs, smallest size first (the easiest to debug), then counts the rest:

```text
$ cstudy test --stress 30
two-sum · python · 4 cases (2 visible, 1 hidden, 1 generated) · 30 oracle inputs (seeds 1-30)

PASS     ex1        0.04ms
PASS     ex2        0.03ms
PASS     2 hidden cases
FAIL     oracle-14  oracle · n=4
         input     nums=[-1564, 1093, 522, 876]  target=1969
         expected  [1, 3]  (unordered, oracle brute-force)
         actual    [0, 0]
FAIL     oracle-28  oracle · n=4
         ...
FAIL     oracle-1   oracle · n=5
         ...
         8 more oracle inputs did not pass
PASS     19 oracle inputs

23/34 passed · 11 failed · total 1.2s
```

`cstudy test --stress 1 --seed 14` reruns the first one alone.

#### Debugging

`cstudy test <file> --debug` runs the normal judged run with the runner waiting for an IDE debugger ([debug mode](runners.md#debug-mode) has the agents, ports and markers): breakpoints in your file stop the real runner, and the verdict comes when the run ends.

| Language | Agent | Default port | `--debug-connect` |
|----------|-------|--------------|-------------------|
| Python | debugpy (`python/.venv`) | 5678 | usage error |
| TypeScript | Node inspector, `--inspect-wait` | 9229 | usage error |
| Java, Kotlin | JDWP, `suspend=y` | 5005 | the JVM connects to an IDE that is listening |
| Go | Delve (`dlv exec --headless`), with a build without optimizations | 2345 | usage error |
| Rust | `debugserver` (macOS) or `lldb-server gdbserver` (Linux), with the dev profile | 12345 | usage error |

The ready line is a stable contract: IDE tasks and run configurations match it. It is printed once, to **standard error**, as plain text on a line of its own, after the agent is bound (so the IDE can attach at once), or, with `--debug-connect`, as the JVM is started:

```text
cstudy: waiting for debugger on 127.0.0.1:5678 (python)
cstudy: waiting for debugger on 127.0.0.1:9229 (typescript)
cstudy: waiting for debugger on 127.0.0.1:5005 (java)
cstudy: waiting for debugger on 127.0.0.1:2345 (go)
cstudy: waiting for debugger on 127.0.0.1:12345 (rust)
cstudy: connecting to debugger at 127.0.0.1:5005 (kotlin)
```

`cstudy: waiting for debugger on` and `cstudy: connecting to debugger at` start the two forms; the port and the language are the last fields. Every other notice of a debug run (`warming Gradle daemon`, `computing expected values`) goes to standard error too, and the report goes to standard output when the run ends.

| Rule | Detail |
|------|--------|
| One language | The language of the file, `--lang` or the active attempt, as for any run |
| Excluded | `--watch`, `--perf`, `--json`, `--stress`, `--seed` and `--time-limit` exit 3 (`--debug excludes --watch, --perf`); `--no-time-limit` is accepted. `--debug-port` and `--debug-connect` without `--debug` exit 3, as does `--debug-connect` for any language but Java and Kotlin |
| No limits | No hello timeout, hang guard or time limit; the runner is never restarted. A concurrent problem runs its sequential cases only (`stress runs are skipped while debugging`) |
| Report | The header names the run (`two-sum · python · debug · 16 cases ...`); no durations, no `total`, no `TLE`, since pauses at breakpoints would be part of them. A pass ends with `all passed (debug run: not recorded; cstudy test records the run)` |
| Not recorded | A debug run is not stored in `test_runs`, never counts as the first pass and unlocks no level; run `cstudy test` again to record it |
| Interrupted | Ctrl-C exits 130, SIGTERM 143 and SIGHUP 129; each kills the runner's process group and any process still running a binary from the run's scratch directory (a Rust runner that a debug server started in its own group), so the port is free again |
| Environment errors (exit 4) | `debugpy` missing from `python/.venv` (the message gives the fix, `uv add --dev debugpy --directory python`); Delve missing (``cannot debug go: dlv was not found; run `go install github.com/go-delve/delve/cmd/dlv@v1.27.2` `` with a link to the [toolchains guide](../guides/toolchains.md#go)), or Rust's debug server (``cannot debug rust: debugserver was not found; run `xcode-select --install` ``, [toolchains guide](../guides/toolchains.md#rust)); a port in use (`cannot debug python: port 5678 on 127.0.0.1 is already in use; stop the other debug session or choose another port with --debug-port`); no IDE listening with `--debug-connect` after 10 s (`no debugger listening on 127.0.0.1:5005; start the IDE's 'Debug JVM (listen)' configuration first`); a runner that ends before it starts the run (`the debug session ended before the run started`, with the runner's last output lines) |

#### JSON output

`cstudy test --json` prints one document per run and exits as the report would. Progress notices (`computing expected values ...`, `warming Gradle daemon ...`, `compiling the Go runner and standard library (first run)`, `compiling the Rust runner (first run)`) go to standard error; an error that stops the run before it starts (no attempt, unknown case) prints `error: ...` and no document.

```json
{
  "slug": "two-sum", "language": "kotlin", "attempt_id": 12,
  "outcome": "failed", "exit_code": 1, "every_case": true,
  "comparator": "unordered", "time_limit": "5x",
  "timer": {"elapsed_s": 751, "limit_s": 1500},
  "levels": null,
  "build": {"seconds": 1.8, "note": "gradle, warm", "diagnostics": []},
  "load_error": null,
  "cases": [
    {"id": "ex1", "visible": true, "generated": false, "status": "pass", "duration_ns": 40000},
    {"id": "h3", "visible": false, "generated": false, "status": "fail", "duration_ns": 31000,
     "input": {"nums": [-3, 8, 0, 3], "target": 0}, "expected": [0, 3], "actual": [3, 3],
     "reason": null},
    {"id": "g1", "visible": false, "generated": true, "status": "tle", "duration_ns": 412000000,
     "time_limit_ms": 95.0, "time_limit_basis": "5x hash-map, calibrated"}
  ],
  "oracle": null,
  "stress": [],
  "tally": {"total": 14, "passed": 12, "failed": 1, "errored": 0, "timed_out": 0, "tle": 1},
  "duration_s": 2.6
}
```

| Field | Rule |
|-------|------|
| `outcome` | `passed`, `failed`, `build_failed` (with `build.diagnostics`) or `load_failed` (with `load_error`: `type`, `message`, `trace`); `cases` and `stress` are empty in the last two |
| `status` | The text status in lower case: `pass`, `fail`, `error`, `timeout`, `tle`, `invalid`, `stalled`, `not_run` |
| `cases` | Every case in run order, passing hidden ones included. A case that did not pass adds what the report prints: `input` (the `tests.json` encoding: arguments by name, or `ops` and `args`, cut after the failing operation), and `expected`, `actual` and `reason` for a wrong answer; `error`, `op_index` and `partial_output` for an exception; `reason` for invalid output or a case not run; `hang_guard_ms` for a timeout; `exit_code` and `stderr` for a crash; `time_limit_ms` and `time_limit_basis` (null for an absolute limit) instead of the input for `tle`. `note` and `stdout` appear when set |
| `stress` | Concurrent problems: the shape [above](#concurrent-problems), with every failing run rather than the first 3 |
| `oracle` | With `--stress N` on other problems: `{"approach": "brute-force", "inputs": [...]}`, each input a case object plus its `seed` and `n`, in seed order (empty when the code did not build or load); else null. Oracle inputs are not in `cases` |
| `levels` | Progressive problems: `ran_up_to`, `last`, `unlocked`, `newly_unlocked`; else null |
| `timer` | With `cstudy start --timer`: seconds elapsed and the time box; else null |
| `tally` | What `test_runs` stores: the problem's cases and stress verdicts, without oracle inputs |
| `diagnostics` | The run's [diagnostics](#diagnostics), after `load_error`: one per error of the compiler's report in `build.diagnostics` (which keeps the compiler's lines as text; a line no parser reads is a diagnostic of its own) and one for a load error; empty when the code built and loaded |
| `perf` | With `--perf`: `{"verdict", "confidence", "text", "warnings", "wrong_answer"}` as the [`perf_result` event](#events) holds them, or null when the check did not run (a case failed); without `--perf`, null |

## cstudy submit

```text
cstudy submit [<slug|file>] [--level N] [--json | --events]
```

Grades a [project problem](problem-format.md#project-problems): every case of levels 1 to the unlocked level, visible and hidden, through the runner ([grading job](runners.md#grading-job)), judged by the core with the problem's comparator. A submission that passes every case of every unlocked level opens the next level.

| Rule | Detail |
|------|--------|
| Subject | The active attempt, or the attempt in progress of `<slug>`; none exits 3. A problem of another kind exits 3: `cstudy submit is for project problems; cstudy test grades two-sum` |
| `--level N` | Grades levels 1 to N; N above the unlocked level exits 3 (`level 3 is locked; pass level 2 with cstudy submit first`). With N below the unlocked level the submission is stored but opens nothing and does not count for [`cstudy done`](#cstudy-done) |
| Unlock | A submission of every unlocked level that passes every case opens the next level: it rewrites the statement, writes that level's [test file](problem-format.md#generated-test-files), records the time and prints the methods the level adds. One submission opens at most one level |
| Last level | A submission that passes every case of every level is the full pass (`first_pass_at`) and prints `all passed · every level done. Next: cstudy done --rating easy\|ok\|hard` |
| Visible cases | Listed with their status; a failing one shows input, expected and actual |
| Hidden cases, practice | Passing ones collapse into a count per level; a failing one shows its id, input, expected and actual (PRD Q10) |
| Hidden cases, mock | In an attempt with mode `mock`, only the number of failing hidden cases per level: no id, input or output, also with `--json` |
| Stored | Every submission, in `submissions`, with a tally per level ([progress-and-scheduling](progress-and-scheduling.md#project-attempts)). A submission whose code does not load is stored too, with every graded case counted as errored |
| No `--debug` | Grading is never debugged: copy a failing case into a test of your own and run `cstudy test --debug` |

```text
$ cstudy submit
bank-project-python · python · submit levels 1-2 of 4 · timer 33:05 / 90:00

level 1  PASS     5/5 (2 visible, 3 hidden)
level 2  FAIL     4/5 (2 visible, 3 hidden)
FAIL     h3    hidden · level 2
         input     ops ["Bank", "create_account", ...]  args [[], [1, "zoe"], ...]
         expected  ["abe(60)", "zoe(60)", "mia(0)"]
         actual    ["zoe(60)", "abe(60)", "mia(0)"]

9/10 passed · level 3 opens when levels 1-2 pass
```

A full pass of the unlocked levels ends with:

```text
10/10 passed · level 3 unlocked: Scheduled transfers
add        schedule_transfer(timestamp: int, source_id: str, target_id: str, amount: int, delay: int) -> str, cancel_transfer(timestamp: int, account_id: str, transfer_id: str) -> bool
tests      tests/test_level_3.py (2 tests)
statement  .statements/bank-project-python.md (updated)
```

In a mock attempt the failing hidden case collapses: `level 2  FAIL     4/5 (2 visible, 3 hidden) · 1 hidden case failed`.

Exit 0 when every graded case passed, 1 when one did not, 2 when the code did not load (`load_error`: the expected module and class, or in Java and Kotlin the compiler's lines when the main sources do not compile; the test sources are not compiled for grading), 3, 4.

`--json` prints one document in the style of [`cstudy test --json`](#json-output): `slug`, `language`, `attempt_id`, `mode`, `outcome` (`passed`, `failed` or `load_failed`), `exit_code`, `every_level` (whether it graded every unlocked level), `timer`, `levels` (`graded_up_to`, `last`, `unlocked`, `newly_unlocked`, and `methods_added`, the methods of a newly opened level in the language's names, else empty), `level_tallies` (per level: `level`, `total`, `passed`, `visible_total`, `visible_passed`, `hidden_total`, `hidden_passed`), `load_error`, `diagnostics` (the [diagnostics](#diagnostics) of code that did not load, else empty; a compile error is read into one diagnostic per error, as for `cstudy test`), `cases` (as in `cstudy test --json`, each with its `level`; in a mock attempt hidden cases are left out and only `level_tallies` counts them), `tally` and `duration_s`.

`--events` writes the submission as an [event stream](#event-stream) instead of the report.

## Event stream

`cstudy test --events` on every autograded problem (function, design, progressive, concurrent, and project, the debugging track's problems included) and `cstudy submit --events` write the run as a stream of events instead of the report: newline-delimited JSON on standard output, one object per line, each line written and flushed as soon as `cstudy` has it. It is the boundary the local web UI builds on to show a run as it happens ([ADR 0014](../decisions/0014-project-problems.md), [ADR 0015](../decisions/0015-local-web-ui.md)): a page run is this command, relayed. `schemas/events.schema.json` describes every event.

```text
$ cstudy submit --events
{"type": "run_start", "version": 1, "command": "submit", "slug": "bank-project-python", "language": "python", "attempt_id": 7, "mode": "new", "levels": {"up_to": 1, "unlocked": 1, "last": 4}, "kind": "project", "track": "practical", "timer": null, "time_limit": null, "planned": null}
{"type": "case_result", "version": 1, "id": "ex1", "visible": true, "generated": false, "status": "pass", "duration_ns": 41000, "level": 1}
{"type": "case_result", "version": 1, "id": "h1", "visible": false, "generated": false, "status": "fail", "duration_ns": 38000, "input": {"ops": ["Bank", "create_account"], "args": [[], [1, "zoe"]]}, "expected": [null, true], "actual": [null, false], "reason": null, "level": 1}
{"type": "level_result", "version": 1, "status": "fail", "level": 1, "total": 2, "passed": 1, "visible_total": 1, "visible_passed": 1, "hidden_total": 1, "hidden_passed": 0}
{"type": "run_end", "version": 1, "outcome": "failed", "exit_code": 1, "message": null, "summary": {"slug": "bank-project-python", ...}}
```

A single-file run, with a time limit that turns one case into `TLE` once the run has calibrated it:

```text
$ cstudy test two-sum --lang kotlin --time-limit --events
{"type": "run_start", "version": 1, "command": "test", "slug": "two-sum", "language": "kotlin", "attempt_id": 12, "mode": "new", "levels": null, "kind": "function", "track": "dsa", "timer": {"elapsed_s": 751, "limit_s": 1500}, "time_limit": "5x", "planned": {"cases": 14, "visible": 2, "hidden": 11, "generated": 1, "oracle_inputs": 0, "stress": null}}
{"type": "build", "version": 1, "seconds": 1.8, "note": "gradle, warm"}
{"type": "case_start", "version": 1, "id": "ex1", "visible": true, "level": null}
{"type": "case_result", "version": 1, "id": "ex1", "visible": true, "generated": false, "status": "pass", "duration_ns": 40000, "level": null}
...
{"type": "case_result", "version": 1, "id": "g1", "visible": false, "generated": true, "status": "pass", "duration_ns": 412000000, "level": null}
{"type": "case_revised", "version": 1, "id": "g1", "visible": false, "generated": true, "status": "tle", "duration_ns": 412000000, "time_limit_ms": 95.0, "time_limit_basis": "5x hash-map, calibrated", "level": null}
{"type": "run_end", "version": 1, "outcome": "failed", "exit_code": 1, "message": null, "summary": {"slug": "two-sum", ...}}
```

### Rules

| Rule | Detail |
|------|--------|
| Lines | Every line is one JSON object whose first fields are `type` and `version`. Standard output holds nothing else; `error: ...` goes to standard error, as for any command |
| `--json` | A final summary, where events are a stream: `run_end` carries the document `--json` prints, so the two flags exclude each other (`--events excludes --json`, exit 3) |
| Excluded | `--watch` and `--debug` exit 3 (`--events excludes --watch`). `cstudy test` on a non-autograded item exits 3 with or without `--events` |
| Accepted | Every other flag of the run: `--level`, `--case`, `--all` (which changes nothing: every case is an event), `--typecheck`, `--stress`, `--seed`, `--time-limit`, `--no-time-limit` and `--perf` |
| Exit codes | Those of the run without `--events`; `run_end.exit_code` is the exit code of the process |
| Signals | SIGINT ends the run as Ctrl-C does: `run_end` with outcome `interrupted` and exit 130. SIGTERM does the same with exit 143, so a program that started the run can stop it with either. Both kill the runner's process group and store nothing |

### Version

`version` is 1. It changes only when an event changes incompatibly: a field removed or renamed, a field's type changed on a stream an earlier `cstudy` wrote, or an ordering rule dropped. New event types, new fields, new values of an enumeration, and fields that may be null on streams no earlier `cstudy` wrote keep the version, so a reader ignores the types and fields it does not know. Every line of a project stream that `cstudy` wrote before `--events` covered every kind is still valid and means the same: those streams only gain the fields `kind`, `track`, `timer`, `time_limit` and `planned` of `run_start`, and the exit code 143.

### Events

"Single-file" below means every autograded kind but `project`.

| `type` | Command | Fields | When |
|--------|---------|--------|------|
| `run_start` | both | `command` (`test` or `submit`), `slug`, `language`, `attempt_id`, `mode` (`new`, `review` or `mock`), `levels`: `up_to` (the last level the run covers), `unlocked` and `last`, or null for a kind without levels; `kind` (`function`, `design`, `progressive`, `concurrent` or `project`), `track`; `timer`: `elapsed_s` at the start and `limit_s`, or null without a time box; `time_limit`: the value in effect (`"5x"`, `"1500ms"`), or null when time limits are off; `planned`, below | Once the options are checked, before the run's work begins |
| `output` | both | `text`: a progress notice the report would print, such as `computing expected values ...` or `warming Gradle daemon ...` | As it happens |
| `build` | `test`, single-file | `seconds` and `note`, as `build` in [`cstudy test --json`](#json-output) (`gradle, warm`) | When the build or the type check ends, for a language or option that has one (Java, Kotlin, Go, Rust, TypeScript with `--typecheck`), whether it succeeded or not |
| `test_start` | `test`, project | `id`: the test id, as in `test_result` | As the runner starts the test, a test file it collects included |
| `test_result` | `test`, project | An entry of `cases` in [`cstudy test --json`](#project-problems) on a project problem: `id`, `status`, `duration_ns`, `origin`, `level`, and `message`, `expected`, `actual`, `error` and `stdout` when set | As the test ends: once per test the suite reported, a test file that failed to collect included |
| `case_start` | `submit`; `test`, single-file | `id`, `visible` and `level` of the case (null for a kind without levels); for an oracle input also `oracle: true`, `seed` and `n` | As the runner starts the case or oracle input; a mock submission writes none for hidden cases |
| `case_result` | `submit`; `test`, single-file | An entry of `cases` in [`cstudy submit --json`](#cstudy-submit) or [`cstudy test --json`](#json-output), with its `level`; for an oracle input an entry of `oracle.inputs`, with `oracle: true`, `seed` and `n` | As the case ends and is judged by the comparator: once per graded case and oracle input; a mock submission writes none for hidden cases, which only `level_result` counts. Its `status` is never `tle`: a time limit is judged after the run, in `case_revised` |
| `case_revised` | `test`, single-file | The case's entry again, complete, with its final `status` (`tle`) and `time_limit_ms` and `time_limit_basis` | Once per case whose verdict the time limit changed, after the time limits are resolved |
| `stress_run_start` | `test`, concurrent | `id` (the stress case), `variant` (as `stress` in `cstudy test --json` names it, such as `platform` or `virtual`), `run` (0-based) and `seed` | As the runner starts the run |
| `stress_run` | `test`, concurrent | `id`, `variant`, `run`, `seed`, `status` (`pass`, `fail`, `error`, `invalid`, `stalled`, `timeout`, or `not_run` for a run left not run when restarts ran out), `duration_ns`, and `reasons` (the run's verdict reasons as the report prints them; empty on `pass`) | As the run ends and is judged against its invariants |
| `stress_result` | `test`, concurrent | An entry of `stress` in `cstudy test --json`: `id`, `variant`, `status`, `runs`, `runs_passed`, `median_ms`, `failures` | Right after the last `stress_run` of its stress case and variant |
| `diagnostic` | both | One [diagnostic](#diagnostics) | Once per diagnostic |
| `level_result` | `submit` | An entry of `level_tallies` in `cstudy submit --json`, plus `status`: `pass` when every graded case of the level passed, else `fail` | Once per graded level |
| `level_unlocked` | `submit`; `test`, progressive | `level`, `title`, `methods` (the methods the level adds, in the language's names, as `methods_added`; empty when it adds none), `tests` (`path` of the level's generated test file relative to the project folder, and `count`, its tests; null for a progressive problem) and `statement` (the rewritten statement's path) | When the run opened a level |
| `perf_result` | `test`, with `--perf` | `verdict` (`optimal`, `near-optimal`, `suboptimal` or `unknown`, null after a wrong answer), `confidence` (`high`, `medium`, `low`, or null), `text` (the verdict line the report prints), `warnings` (the report's `warning` lines, as text) and `wrong_answer` (the `FAIL wrong answer at n=...` line, or null) | After the short bench of `--perf`, which runs only when every case passed |
| `run_end` | both | `outcome`, `exit_code`, `message` and `summary` | Last |

`planned` says what the run will report, so a reader can show progress against it: for a single-file `test`, `{"cases", "visible", "hidden", "generated", "oracle_inputs", "stress"}`, the counts the report's header prints, with `stress` `{"cases", "variants", "runs"}` for a concurrent problem (runs per stress case and variant) or null; for a project run, null, since a suite's size is known only as it runs.

`run_end.outcome` is the `outcome` of the `--json` document (`passed`, `failed`, `build_failed` or `load_failed`), `error` when the run stopped after `run_start` (an environment error such as pytest missing from `python/.venv`, a `--case` that names no test, an internal error), or `interrupted` (SIGINT, exit 130; SIGTERM, exit 143). `summary` is the document `--json` prints, or null for `error` and `interrupted`; `message` is the error's text for `error`, else null.

### Events by kind

| Kind | Results | Also |
|------|---------|------|
| Function, design (the debugging track's `stub: buggy` problems are these kinds) | `case_start` and `case_result` per case, then per oracle input with `--stress N` | `build`, `case_revised` with a time limit, `perf_result` with `--perf` |
| Progressive | `case_start` and `case_result` per case of levels 1 to `levels.up_to`, each with its `level` | `level_unlocked` when the run opened a level; `build`, `case_revised` |
| Concurrent | `case_start` and `case_result` per sequential case, then `stress_run_start` and `stress_run` per stress run, and `stress_result` per stress case and variant | `build`, `case_revised` for sequential cases |
| Project, `test` | `test_start` and `test_result` per test | |
| Project, `submit` | `case_start` and `case_result` per graded case | `level_result` per level, `level_unlocked` |

Timing is in the fields, not in the order of the lines: `duration_ns` on each result (the call or the test only, as the runner measures it), `seconds` on `build`, `median_ms` on `stress_result`, `timer` on `run_start`, and `duration_s` in the `run_end` summary. Events carry no clock time: a reader sees each line as it is written.

### Ordering

| Rule | Detail |
|------|--------|
| Bounds | `run_start` is the first line and `run_end` the last. A run that stops before it starts (no attempt, a locked level, `submit` on another kind of problem, a usage error in the options) writes no event, only `error: ...` on standard error, as `--json` writes no document. Once `run_start` is written, `run_end` follows unless the process is killed |
| Output | `output` may come anywhere between `run_start` and `run_end` |
| Build | `build` comes before the first start or result |
| Results | `test_result`, `case_result` and `stress_run` come in run order: the suite's order for tests; for cases, `tests.json` order, then oracle inputs in seed order, then stress runs in the order the runner runs them. A start comes before the result of its test, case or stress run, and no other one's event comes between them. A result comes without a start when the runner never started its test or case: a hang or crash between cases is recorded on the next case, and a case left not run when restarts ran out comes, with status `not_run`, after the results the runner reported |
| Revisions | `case_revised` comes after every result and `stress_result`, in the order of the cases it revises; a case is revised at most once |
| Diagnostics | `diagnostic` comes after `run_start` and before the first `level_result`, or before `level_unlocked`, `perf_result` and `run_end` in `cstudy test` |
| Levels | `level_result` comes after every `case_result`, in level order, then `level_unlocked`; in `cstudy test`, `level_unlocked` comes after every result and revision |
| Perf | `perf_result` comes after everything but `run_end`, and only when every case passed; `output` lines of its bench may precede it |
| Timing | Each start and result is written as the runner reports it, while the run goes on, so a reader can show the test in progress. A result that ended in a hang is written when the hang guard expires. The time between a start and its result includes the runner's own work; `duration_ns` is the test's or call's duration |

### Diagnostics

A diagnostic says where code does not load, build or type-check, so an editor can mark the place.

| Field | Meaning |
|-------|---------|
| `source` | `load` (the runner could not load the code, or the framework could not collect a test file), `typecheck` (a type checker, such as `tsc --noEmit` for `--typecheck`) or `build` (a compiler) |
| `severity` | `error`, `warning` or `info` |
| `file` | Relative to the project folder for a project problem, and to the workspace root for any other (`python/practice/two_sum.py`), or null when the report names no file |
| `line`, `column` | 1-based, or null when the report names none; a runner's trace never names a column |
| `code` | The tool's name for the problem: the exception type (`SyntaxError`, `SymbolNotFound`) or a compiler's code (`TS2322`); null when it has none |
| `message` | The tool's message; the exception type when the message is empty |

A `load` diagnostic comes from a [load error](runners.md#event-stream---out-json-lines):

| Load error | Where it points |
|------------|-----------------|
| The grading job's, or a test file that failed to collect (a result whose id is the file, which stays a `test_result` with status `error` as well) | The innermost frame of the error's trace: `bank/bank.py:12 in Bank.deposit` gives `bank/bank.py`, line 12. `code` is the error's type |
| The suite's own, when the framework refused to run it, such as a `conftest.py` that does not import | Read from the framework's report: the innermost frame of its Python traceback that lies in the project folder, an absolute path made relative to the folder, and the traceback's last exception as `code` and `message` (`E   SyntaxError: invalid syntax`) |

Diagnostics are `diagnostic` events, and the `diagnostics` list of `cstudy test --json` and of `cstudy submit --json`. On a single-file problem a load error points at the innermost frame of its trace that lies in a file of the problem ([solution file targets](#solution-file-targets)), a trace's bare file name (`two_sum.py:7 in two_sum`) naming the user file, and each line of a failed build (`build.diagnostics`) is read by the parser for its tool as below. An error without such a frame gives a diagnostic without a place, and one without an exception line keeps its own type and message. Test files that fail on the same line of one module give one diagnostic. An exception a test raises while it runs is a test result, not a diagnostic. A type checker's or compiler's report is read by a parser for its format into the same fields. For `tsc`, each line `src/bank.ts(3,5): error TS2322: <message>` is one diagnostic, with its category (`error`, `warning`, or `message` and `suggestion` as `info`) as `severity`, its code as `code`, and the indented lines below it continuing `message`; a path outside the project folder is given from the folder (`../../typescript/support.ts`), and a line without a place, such as `error TS5083: ...`, has none. A checker without a parser, or a report its parser finds no diagnostic in, gives each line as a diagnostic without a place.

A failed build (source `build`) is read the same way, by the parser for the language's compiler, from the compiler's lines in `build.diagnostics`:

| Compiler | Diagnostic lines | `severity` | `code` | Message continues with |
|----------|------------------|------------|--------|------------------------|
| `javac` (Java) | `<path>:12: error: <message>`, then the source line and a caret line whose caret gives `column` | `error`, `warning`; a `Note:` line is `info`, with its file when it names one and no line | A lint category in brackets, such as `removal`; none for an error | The indented lines below the caret (`symbol:`, `location:`) |
| `kotlinc` (Kotlin), as Gradle prints it | `e: file:///<path>:12:5 <message>` | `e:` error, `w:` warning, `i:` info | None; Kotlin names none | Indented lines directly below |
| `go build`, `go vet` (Go) | `<path>:12:5: <message>`, or without the column; `vet: ` and `./` before the path are dropped, and `# package` lines are left out | `error` | None | The tab-indented lines below (`have (...)`, `want (...)`) |
| `cargo build` (Rust), as the runner reports it | `<path>:12:5: error[E0599]: <message>` | `error`, `warning` | The error code in brackets, such as `E0599` | The label, `note:` and `help:` lines below, up to the next diagnostic |

Whatever the path a compiler names (absolute, a `file://` URL, relative to the directory it ran in), `file` is the problem's: on a single-file problem the user file or, in Java, Kotlin and Go, a file of its package directory, from the workspace root; on a project the file relative to the project folder. A file that is not the problem's (a reference, a runner or generated file) keeps its message and has no `file`, `line` or `column`. The project's compile errors are read from the compile error that stops the run: the suite's own for Java and Kotlin, and the result of the package or test target that did not compile for Go and Rust. Each error in them is a diagnostic in place of the one diagnostic of that load error, and an error that is the same on a package and on the package of its tests is given once.

## cstudy status

```text
cstudy status [<slug|file>] [--json]
```

Shows where an attempt in progress stands, for every kind of problem and for non-autograded items, without running anything. The lines a kind has no value for are left out: `submitted` and `files` are for [project problems](problem-format.md#project-problems), `level` for progressive and project problems, `tested` for autograded problems.

| Line | Content |
|------|---------|
| Header | Slug, language (none for an item), kind (`function`, `design`, `progressive`, `concurrent`, `project`, or the item's track), attempt id and mode |
| `file` | The file `cstudy start` wrote: the stub, the project folder or the notes |
| `level` | The unlocked level, of the last, with its title; for a project, when it opened |
| `timer` | Elapsed and time box, with `--timer`; else absent |
| `hints` | Hints used of the problem's hints, and for a project `next opens with level N` while the next hint is locked; absent for a problem without hints |
| `solution` | `revealed, graded as again` once `cstudy solution` marked the attempt, or `revealed` for an item, whose grade revealing never lowers; else absent |
| `tested` | The latest `cstudy test`: passed of total, and how long ago. A run older than a level's opening covered none of that level's tests, so the line then ends with the first level that opened after it: `2/2 passed, 12 min ago, before level 2 opened` |
| `submitted` | The latest submission's tally per level, and how long ago; `best` adds the highest passed count per level over the attempt when it differs |
| `files` | Starter files changed and removed, and files added, under `projects/<slug>/`, by content against what the starter provided (the folder's [manifest](installation-and-workspaces.md#project-folders)); generated test files, `.venv` and caches are left out |
| `next` | Project: `cstudy test --watch` before any submission, `cstudy submit once level <n> passes`, or `cstudy done --rating easy\|ok\|hard` after the full pass. Other problems: `cstudy test --watch` until a run passes every case (of the last level, for a progressive problem), then `cstudy done --rating easy\|ok\|hard`, or `cstudy done --gave-up` once you stop. Items: `answer in the notes, then cstudy solution <slug>`, as `cstudy start` prints it |

```text
$ cstudy status
bank-project-python · python · project · attempt 41 · new
file       projects/bank-project-python
level      2 of 4: Top spenders (opened 18:02)
timer      33:05 / 90:00
hints      1 of 4, next opens with level 3
tested     3/4 passed, 1 min ago
submitted  level 1 5/5 · level 2 4/5, 2 min ago
files      2 changed, 1 added, 0 removed against the starter
next       cstudy submit once level 2 passes
```

```text
$ cstudy status two-sum
two-sum · kotlin · function · attempt 12 · new
file       jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt
timer      12:31 / 25:00
hints      0 of 2
tested     12/14 passed, 3 min ago
next       cstudy test --watch
```

`--json` writes the same values: `slug`, `kind` (as in [`cstudy list --json`](#cstudy-list): `item` for an item), `track`, `language` (null for an item), `attempt_id`, `mode`, `started_at`, `file` (the `file` line's path), `hints` (`used`, `total`, 0 for a problem without hints and for an item, and `locked_until_level`, the level the next hint opens with while it is locked, else null), `solution_revealed`, `statement` (its path), `levels` (`unlocked`, `last`, `titles` of the open levels, `opened_at` per open level), `timer`, `last_test_run` (`ran_at`, `total`, `passed` and `predates_level`, the first level that opened after the run or null, or null without a run), `latest_submission` (`submitted_at`, `level_tallies`, or null), `best_per_level` (`level`, `passed`, `total`), `files` (`changed`, `added`, `removed`, each a sorted list of paths relative to the folder, and `entries`, below) and `next`. In a mock attempt the tallies count hidden cases but name none. A value a kind does not have is null (`levels` without levels, `last_test_run` for an item, `latest_submission` and `files` but for a project) or empty (`best_per_level`); `levels.opened_at` holds a project's opening times and is empty for a progressive problem, whose openings are not stored.

`files.entries` is the folder's tree for an interface that shows it: every file under the folder, untracked ones aside, and every file `cstudy` provided that the folder lacks, in path order, each with `path` (relative to the folder), `origin`, `level` and `state`.

| `origin` | `level` | `state` |
|----------|---------|---------|
| `starter`: a file the starter provided | null | `unchanged` while its content is what `cstudy` provided, `modified` once it differs, `deleted` when the folder lacks it |
| `level`: the [generated test file](problem-format.md#generated-test-files) of an open level | its level | the same: `modified` is a test file you edited |
| `yours`: any other file | null | `added` |

Without a manifest (a folder started before `cstudy` kept one, or a clone), `status` compares the folder with what `cstudy` provides now: the starter and the generated test files of the open levels. It writes no manifest; the next `cstudy start` does.

Exit 0; 3 without an attempt in progress.

## cstudy history

```text
cstudy history <slug|file> [--json]
```

Shows one problem's or item's past in this workspace: its review schedule and every attempt, newest first, with the runs each recorded. It reads `progress.db` only.

```text
$ cstudy history two-sum
two-sum · easy · arrays-hashing · passed
review     due 2026-10-27 (in 3 days) · interval 7d · ease 2.50 · reps 2 · lapses 0

ATTEMPT  LANG    MODE    STATUS       STARTED           TIME     RATING  GRADE  HINTS  TESTS  BENCH
14       kotlin  review  passed       2026-10-24 09:12  18m 40s  ok      ok     0      3      optimal
9        python  new     failed       2026-10-17 20:01  41m 02s  -       again  2      7      -
8        python  new     abandoned    2026-10-17 19:30  -        -       -      0      1      -
```

| Rule | Detail |
|------|--------|
| Header | Slug, difficulty, the pattern or track, and the [problem status](progress-and-scheduling.md#problem-status) |
| `review` | The `schedule` row: due date and how far off (`in 3 days`, `today`, `2 days ago`), interval, ease, reps and lapses; `not scheduled` without one |
| Attempts | Every attempt of the slug in every language, newest first: id, language (`-` for an item), mode, status, start, solve time (`-` while in progress or abandoned), rating, grade (`again`, `hard`, `ok`, `easy`), hints used, test runs (or submissions, for a project), and the latest bench verdict. A revealed solution adds `solution` after the grade. Each column is as wide as its widest value. None: `no attempts yet` |
| `--json` | `{"slug", "kind", "track", "status", "schedule": {"due_on", "interval_days", "ease", "reps", "lapses", "last_grade"} or null, "attempts": [...]}`, with `kind` as in [`cstudy list --json`](#cstudy-list) (`item` for an item) and the attempts newest first, each attempt with `attempt_id`, `language`, `mode`, `status`, `started_at`, `ended_at`, `solve_s` (null while in progress or abandoned), `rating`, `grade` and `last_grade` (`again`, `hard`, `ok`, `easy`, or null), `hints_used`, `solution_revealed`, `time_limit_s`, `level_unlocked`, `levels_finished` (projects, else null), and its rows: `test_runs` (`ran_at`, `total`, `passed`, `failed`, `errored`, `timed_out`, `tle`, `time_limit`, `duration_ms`), `submissions` (`submitted_at`, `graded_up_to`, `every_level`, `levels`, `total`, `passed`, `duration_ms`; empty but for a project) and `bench_runs` (`ran_at`, `verdict`, `confidence`, `ratio`, `reference_id`), each list oldest first |

Exit 0; 3 for an unknown slug.

## cstudy hint

```text
cstudy hint [<slug|file>]
```

Prints the next unrevealed `### Hint N` from `problem.md` and increments `hints_used` on the active attempt. Prints `no more hints` when exhausted (exit 0, `hints_used` unchanged). The next hint is number `hints_used + 1`, so hints are counted per attempt. Locked (exit 3) while a [mock interview](#cstudy-mock) runs.

For a project problem, hints open with levels: of `h` hints across `L` levels, hint `n` opens with level `(n-1)*L//h + 1`. While the next hint's level is locked, `cstudy hint` prints `no more hints until level N opens` (exit 0, `hints_used` unchanged).

```text
two-sum · hint 1 of 2
For each value, which partner would complete the sum?
```

## cstudy solution

```text
cstudy solution <slug|file> [--lang L] [--approach ID] [--all] [--broken[=ID]] [--explanation-only] [--yes]
```

Shows, through `$PAGER`, the explanation's overview table, then for each selected approach its full explanation section followed by its code in the chosen language (syntax highlighted). Default approach: the first `optimal` in `meta.yaml`; `--all` shows every approach in ladder order. If the approach has no file in that language, the explanation is shown with `no <lang> reference; available: python, java`.

`--broken` (concurrent problems) shows a deliberately broken reference instead (default: the first in `concurrency.broken` that has a file in the language) with its `## Broken: <id>` explanation section, as a "spot the bug" exercise; it counts as revealing the solution. The id only follows `=` (`--broken=if-not-while`), as with `cstudy test --time-limit=VALUE`, so in `cstudy solution --broken bounded-blocking-queue` the slug stays an argument. `--broken` with `--approach` or `--all`, on a problem without broken references, or with an unknown id exits 3.

A [project problem](problem-format.md#project-problems) shows its one approach's section, `### Design` included, then the reference: each file the overlay adds in full, and each file it changes as a unified diff against the starter's file. `--lang` may repeat the problem's language; `--approach` and `--all` show the one approach.

Problems with a `rubric.md` (track `lld`) show it right after the title, before the overview: the design criteria for self-review, then the reference design ([format](authoring.md#rubricmd)); `--explanation-only` keeps it.

If the problem has an unsolved `in_progress` attempt, it asks `Reveal the solution? The attempt will be graded as again. [y/N]` (skipped with `--yes`) and sets `solution_revealed`.

Locked (exit 3), for problems and items alike, while a [mock interview](#cstudy-mock) runs.

For a non-autograded item it shows the title, then `rubric.md`, then `reference.md`, without asking: comparing the notes with them is the self-review, so revealing never lowers the grade (an attempt in progress still records `solution_revealed`). `--lang`, `--approach`, `--all` and `--explanation-only` are usage errors for items.

## cstudy done

```text
cstudy done [<slug|file>] (--rating easy|ok|hard | --gave-up) [--notes TEXT]
```

| Rule | Detail |
|------|--------|
| Rating | Required when the latest test run passed all cases: every case of the problem, with a concurrent problem's stress cases counted once per variant, so a Java or Kotlin problem with `jvm_threads: [platform, virtual]` stores twice its stress cases. A run of some cases (`--case`, unlocked levels only) never counts |
| `--gave-up` | Required when it did not; grade `again` |
| Project problems | The latest submission that graded every unlocked level stands in for the latest test run. A rating is required when it passed every case of level 1, `--gave-up` otherwise, also when there is no such submission. The grade is capped by the levels that submission finished ([project attempts](progress-and-scheduling.md#project-attempts)), and the output says so: `bank-project-python · python · failed · levels 3 of 4 · 1h 24m · rating ok, capped at hard · hints 0` |
| Non-autograded items | Rating only (`--gave-up` is a usage error); status `passed`, grade from the rating with no caps |
| Effects | Close the attempt, compute the grade and next due date ([progress-and-scheduling](progress-and-scheduling.md)) |

```text
two-sum · kotlin · passed · 18m 40s · rating ok · hints 0
next review  2026-10-27 (in 3 days) · ease 2.50
```

## cstudy next

```text
cstudy next [--track T]... [--pattern P] [--difficulty D] [--lang L] [--new | --review] [--start | --json]
```

Applies the selection algorithm in [progress-and-scheduling](progress-and-scheduling.md#cstudy-next-selection). `--track` is repeatable and reaches non-autograded items, for example `cstudy next --track system-design`; their `start` line has no `--lang`. `--start` runs `cstudy start` on the result, in the `--lang` language (default `default_lang`) for a problem, and in its own language for a project problem, and prints its report instead of the `start` line; it opens the editor when `open_on_start` is on. `--new` together with `--review`, or a `--pattern` outside the [taxonomy](content.md#pattern-taxonomy), is a usage error (exit 3).

```text
review  merge-intervals  (medium · intervals)  overdue 3d, interval 7d
start   cstudy start merge-intervals --lang kotlin
```

```text
new     koko-eating-bananas  (medium · binary-search)  weakest pattern: binary-search (0.75)
start   cstudy start koko-eating-bananas --lang kotlin
```

A review due today reads `due today, interval 3d`; a new pick from a non-`dsa` group reads `weakest track: practical (0.75)`.

`--json` prints the pick as one document instead: `{"pick": "review" or "new", "slug", "title", "kind", "difficulty", "group", "reason", "language", "start"}`, where `kind` is as in [`cstudy list --json`](#cstudy-list) (`item` for an item), `group` the pick's [weakness group](progress-and-scheduling.md#weakness-score) (the primary pattern of a `dsa` problem, else the track), `reason` the text after the parentheses (`overdue 3d, interval 7d`), `language` the language `--start` would use (null for an item) and `start` the command of the `start` line; with nothing to pick, `{"pick": null, "message": ...}` with the text the report prints. `--json` with `--start` is a usage error (exit 3).

## cstudy list

```text
cstudy list [--track T] [--kind K] [--pattern P] [--difficulty D] [--status S] [--content draft|ready] [--lang L] [--json]
```

`--status`: `new`, `attempted`, `passed`, `due`, `mastered` (definitions in [progress-and-scheduling](progress-and-scheduling.md#problem-status)). `--kind`: `function`, `design`, `progressive`, `concurrent`, `project`, or `item` for the non-autograded items. `--lang` filters to problems whose references cover that language. Non-autograded items follow the problems, ordered by track, `order` and slug, with `-` for the id and the references and their track in the pattern column; `--pattern` and `--lang` leave them out, and `--kind` other than `item` leaves them out.

`--json` prints the same rows as one document, problems then items: `{"today": "2026-10-24", "entries": [...]}`, each entry with `id` (null for an item), `slug`, `title`, `track`, `kind` (`item` for an item), `difficulty`, `patterns`, `languages` (the reference languages, empty for an item), `content` (`draft` or `ready`), `source` (`catalog`, or `workspace` for [your own problems](installation-and-workspaces.md#your-own-problems)), `status`, `due_on` (null without a schedule row) and `in_progress` (each attempt in progress of the slug: `attempt_id`, `language`, `mode`). Exit 0.

```text
ID    SLUG              DIFF    PATTERN          STATUS    DUE         REFS
0001  two-sum           easy    arrays-hashing   passed    2026-10-27  py ts java kt
0002  lru-cache         medium  linked-list      new       -           py ts java kt
0014  koko-eating-...   medium  binary-search    due       2026-10-21  py java
```

## cstudy show

```text
cstudy show <slug|file> [--level N]
```

Prints the rendered statement (title, metadata, sections, examples generated from visible cases, unlocked levels, and for concurrent problems the generated stress-case table; never hints). For a progressive or project problem the unlocked levels are those of the problem's attempt in progress, or level 1 without one, and a project problem's statement uses its language's names and each level's `Methods to add` line; `--level N` shows levels 1 to N and follows the `cstudy test --level` rules. For a non-autograded item it prints the statement `cstudy start` would write (the prompt, the change under review and the located [study guides](content.md#study-guides)) without writing it; `--level` is a usage error.

## cstudy new

```text
cstudy new <slug> [--track T] [--from-template array|tree|design|progressive|concurrent|project-python|project-typescript|project-go|project-java|project-kotlin|project-rust]
              [--title TEXT] [--difficulty D] [--pattern P]
```

Creates `problems/<next id>-<slug>/` from the template `cli/src/coding_study/adapters/templates/<template>/` (package data) with `status: draft`, in the content checkout when the content is one, otherwise in the workspace's own `problems/` with ids from 5001 ([your own problems](installation-and-workspaces.md#your-own-problems)): `problem.md` (required headings with `TODO` placeholder text), `meta.yaml` (template signature), `tests.json` (one visible example; `progressive`: one per level), `generator.py`, `solutions/explanation.md` (one approach section skeleton) and an empty reference file per language. `meta.yaml` lists the languages explicitly (`languages: [python, typescript, java, kotlin, go, rust]`; the `concurrent` template lists the five that fit); a problem in your own workspace may list fewer, so delete the languages you do not practice from that line and their reference files. The output says so. The one approach is `reference` (role `optimal`, and the oracle in the `dsa` templates), because the schema requires an `optimal` approach. Function and class names come from the slug (`max-gap`: `maxGap`, `MaxGap`), in the files' text and, where a file is named after its class, in its path (`starter/src/main/java/app/MaxGap.java`).

| Template | Signature shape | Default track and primary pattern |
|----------|-----------------|-----------------------------------|
| `array` (default) | `function`, params `int[]` and `int`, returns `int` | `dsa`, `arrays-hashing` |
| `tree` | `function`, param `TreeNode`, returns `TreeNode` | `dsa`, `trees` |
| `design` | `class` with constructor and two methods, comparator `ops` | `dsa`, `arrays-hashing` |
| `progressive` | `class` with 4 levels, one method per level, comparator `ops` | `practical`, none |
| `project-python`, `project-typescript`, `project-go`, `project-java`, `project-kotlin`, `project-rust` | `class` with 2 levels, one method per level, comparator `ops`, `languages` the template's one language, a `project` block (Java and Kotlin: `entry: app.<ClassName>`, `tests: src/test/java/app` or `src/test/kotlin/app`); a `starter/` with `README.md`, the build files of [the starter rules](problem-format.md#starter) and the entry file with level 1's method; `tests.json` with one visible case per level; the reference overlay `solutions/reference/` with the entry file; no `generator.py` and no reference file per language | `practical`, none |
| `concurrent` | `class` with a `blocking` method and a plain one, comparator `ops`, a `concurrency` block (`model: threads`, languages java, kotlin, python), one sequential and one stress case, one broken reference | `concurrency`, none |

Defaults: difficulty `medium`; title from the slug (`max-gap`: `Max Gap`). `--track` accepts the autograded tracks only (`dsa`, `practical`, `lld`, `concurrency`, `debugging`); `dsa` needs a primary pattern from `--pattern` or the template. `--track lld` also writes `rubric.md` with the [required sections](authoring.md#rubricmd) in order, each holding `TODO` text (check S8).

Exit 3 if a problem or a non-autograded item already uses the slug, or for an invalid slug, track, pattern or blank title. Prints the [authoring workflow](authoring.md#workflow) from step 2 as next steps, each with its check command. After replacing every `TODO`, each template passes `cstudy verify <slug> --static`.

## cstudy verify

```text
cstudy verify [<slug>...] [--changed] [--track T] [--lang L] [--static]
          [--oracle [--oracle-cases N]] [--ladder] [--conformance] [--require-ready] [--jobs N]
          [--stress N]
```

| Flag | Effect |
|------|--------|
| no slugs | All problems |
| `--changed` | Problems with files changed relative to `main` (git): committed on the branch since it left `main`, staged, unstaged, or untracked and not ignored. Prints `no problems changed relative to main` and exits 0 when there are none; with slugs or `--conformance` it is a usage error (exit 3); git missing, or no `main` to compare with, exits 4 |
| `--static` | Schema and static checks only; no execution |
| `--oracle` | Cross-check every approach against the oracle on N random small inputs (default 200). A problem without `generator.py` prints `oracle n/a` and does not fail |
| `--ladder` | Bench references and check time bands against declared classes: one language at a time after the parallel checks, only where the references passed their cases, memory off, `perf.size_ladder` sizes. Prints `ladder ok` or `ladder FAIL` with the highest 1-minute load the ladders ran at (`ladder ok (load 2.3)`); a reference with fewer than 3 usable sizes is a warning, not a failure. On a busy machine (on battery, or the load above half the cores) a warning names the condition, and a ladder that contradicted its class there is measured once more after the machine settles, 60 s at most ([busy machine](performance-analysis.md#busy-machine)). A problem without `generator.py` prints `ladder n/a` and does not fail |
| `--conformance` | Run the runner conformance suite |
| `--require-ready` | Fail any problem whose `status` is not `ready` |
| `--jobs` | Parallel language runners (default: number of languages). The runners of a concurrent problem's languages still take turns: their builds overlap, but each runs its stress cases alone |
| `--stress N` | Concurrent problems: runs per stress case and variant for D6 and D7 (default 10); D7 requires failures in at least `ceil(0.9 * N)` runs. The line reports the fewest runs a correct reference passed (`stress 10/10`), the slowest correct run as a share of its deadline (`slowest 8%`) and the (broken reference, language, case, variant) combinations caught (`broken caught 11/11`) |

Checks are listed in [authoring](authoring.md#what-cstudy-verify-checks). A [project problem](problem-format.md#project-problems)'s line shows its one language, its cases (D3) and its native suite (D9): `0249-bank-proj...  static ok · py 1/1 ok · suite 14/14`; `--oracle` and `--ladder` print `n/a` for it, and `--lang` with another language leaves it out.

```text
0001-two-sum      static ok · py 2/2 ok · ts 1/1 ok · java 1/1 ok · kt 1/1 ok · oracle 200/200
0014-koko-eat...  static ok · py 2/2 ok · ts - · java 1/1 ok · kt -      draft (coverage 2/4)
0031-word-break   FAIL static: solutions/explanation.md missing "### Correctness" in approach memo-dp
0190-bounded-...  static ok · py 2/2 ok · ts 1/1 ok · java 2/2 ok · kt 2/2 ok · stress 10/10 · slowest 8% · broken caught 11/11

coverage  python 31/31 · typescript 29/31 · java 31/31 · kotlin 28/31
result    1 failed · 30 passed
```

Exit 0, 1, or 5 (static failures only).

## cstudy bench

```text
cstudy bench [<slug|file>] [--lang L] [--sizes LIST] [--reps N] [--refs-only] [--no-memory]
```

Spec: [performance-analysis](performance-analysis.md).

```text
two-sum · python · sizes 1e2..1e5 · reps 7 · power AC · load 1.2

TARGET        DECLARED   n=1e2    n=1e3    n=1e4    n=1e5    SLOPE  BAND     MEMORY
brute-force   O(n^2)     0.21ms   19.8ms   2.04s    budget   2.00   ~n^2     constant
hash-map      O(n)       0.01ms   0.09ms   0.94ms   10.1ms   1.00   ~n|nlogn linear
you                      0.01ms   0.11ms   1.10ms   11.8ms   1.01   ~n|nlogn linear

verdict   optimal: matches hash-map, 1.17x at n=1e5 · confidence high (spread 3%, R^2 0.999)
space     linear, same as hash-map · confidence high
history   best previous 13.0ms at n=1e5 (2026-09-12) · now 9% faster · 1st of 3 runs
```

| Item | Rule |
|------|------|
| Subject | The attempt in progress (for `<slug>`, optionally in `--lang`); with a slug and no attempt in progress, the latest attempt of that problem in `--lang` or `default_lang`; none: exit 3. `--refs-only` with a slug needs no attempt |
| `--sizes` | Comma-separated positive sizes, e.g. `100,1000,10000`; replaces `perf.size_ladder`. Sizes print as `1e2` when they are a digit times a power of ten |
| Cells | Median time per call; `budget` for a call over `perf.budget_ms` (or the hang guard), `error` where the target failed, `-` where it did not run |
| Correctness | The user's output at every size is compared, with the problem's comparator, to the output of the reference that computes expected values: `perf.expected_from` if it has a file in this language, else the first `optimal` one, else any. A difference or an exception prints `FAIL      wrong answer at n=1e3: expected [3, 7], got [3, 3]` and no verdict |
| Warnings | `warning   <text>` lines after the verdicts: environment warnings (confidence capped at medium), recovered hangs and crashes, references that did not load, `beats declared optimal: check references` |
| `--refs-only` | No `you` row and no verdict; stored with `attempt_id` NULL |

Stored in `bench_runs` (a user run whose code does not build or load is not stored). Exit 0 when the bench completed (any verdict), 2 if the user code does not build or load, 1 if the user code fails correctness on a bench input. Concurrent problems have no bench in v1: exit 3 (`bench is not available for concurrent problems`); neither have project problems (`bench is not available for project problems`).

## cstudy stats

```text
cstudy stats [--by pattern|track|lang|difficulty] [--since DATE] [--json]
```

Per group: problems, attempted, passed, mastered, pass rate of the last 10 attempts, median solve time, weakness score; plus finished attempts, the last 7 days, the streak in days, due today, overdue, and the latest bench verdicts. Every value is defined in [progress-and-scheduling](progress-and-scheduling.md#statistics).

| Flag | Effect |
|------|--------|
| `--by` | `pattern` (default): the `cstudy next` group, the primary pattern of a `dsa` problem, else the track; `track`; `lang` (problems only, by the language of each attempt); `difficulty` |
| `--since DATE` | `YYYY-MM-DD`: attempts and bench runs that ended before the local date are left out of the attempt columns, the finished count and the bench line; problems, mastered, weakness, the last 7 days, the streak and the reviews always describe today. Another format exits 3 |
| `--json` | The same values as one JSON document |

Rows follow the taxonomy order, then the track order (`--by track` and `--by lang` the declaration order, `--by difficulty` easy to hard); a group without `ready` content has no row. The group column is as wide as the longest name.

```text
$ cstudy stats
GROUP           PROBLEMS  ATTEMPTED  PASSED  MASTERED  PASS RATE  SOLVE TIME  WEAKNESS
arrays-hashing        17          5       4         1        80%     14m 10s      0.42
two-pointers          10          0       0         0          -           -      0.75
system-design         10          1       1         0       100%     45m 00s      0.30

attempts  6 finished · 5 in the last 7 days · streak 3 days
reviews   1 due today · 1 overdue
bench     4 benched · 2 optimal · 1 near-optimal · 1 suboptimal · 0 unknown
```

With `--since 2026-10-01` the attempts line reads `6 finished since 2026-10-01 · ...`. `--json` writes:

```json
{
  "today": "2026-10-24", "by": "pattern", "since": null,
  "groups": [{"group": "arrays-hashing", "problems": 17, "attempted": 5, "passed": 4,
              "mastered": 1, "recent_attempts": 5, "recent_passed": 4, "pass_rate": 0.8,
              "median_solve_s": 850, "weakness": 0.42}],
  "attempts": {"finished": 6, "last_7_days": 5, "streak_days": 3},
  "reviews": {"due_today": 1, "overdue": 1},
  "bench": {"optimal": 2, "near-optimal": 1, "suboptimal": 1, "unknown": 0}
}
```

`pass_rate` and `median_solve_s` are `null` without attempts or passes; `pass_rate` and `weakness` are rounded to 4 decimals. Exit 0.

## cstudy mock

```text
cstudy mock [--minutes 45] [--count 2] [--track T]... [--lang L]
```

Picks `count` problems with `cstudy next` rules (new only, medium and hard), starts them with a shared timer, disables `cstudy hint` and `cstudy solution` until the timer ends or all are done.

| Flag | Effect |
|------|--------|
| `--minutes` | The shared timer in minutes (default 45) |
| `--count` | How many problems (default 2); when the scope runs out, fewer start and the header says `1 of 2 problems` |
| `--track` | Repeatable, as in `cstudy next`; default `next.tracks`. Non-autograded items take part like problems; their timer never caps the grade |
| `--lang` | Only problems available in the language, started in it; default `default_lang` |

| Rule | Detail |
|------|--------|
| Picks | Step 2 of the [`cstudy next` selection](progress-and-scheduling.md#cstudy-next-selection) over the new `medium` and `hard` problems in scope, so the difficulty gate opens `medium` at once. Each pick comes from a group not picked yet while another group still has a new problem; picked problems count as in progress for the later picks |
| Start | Each pick starts like `cstudy start <slug> --fresh --timer <minutes>m`, with attempt mode `mock`. The attempts start together with the same time box: that is the shared timer. `cstudy test` shows the time left, and `cstudy done` past the timer caps the grade at `hard`, as with `--timer` |
| Project problems | Take part like other problems when the `practical` track is in scope and their language is the mock's; each starts like `cstudy start <slug> --fresh --timer <minutes>m`. In a mock attempt [`cstudy submit`](#cstudy-submit) reports only the number of failing hidden cases per level |
| Lock | While the timer runs and a problem of the mock is unfinished, `cstudy hint`, `cstudy solution` and another `cstudy mock` exit 3: `cstudy hint is locked during the mock interview (group-anagrams, lru-cache; 31:20 left); it unlocks when the timer ends or every problem is done`. The mock is the attempts in progress with mode `mock`; nothing else is stored |

```text
$ cstudy mock
mock interview · 2 problems · 45 min shared timer · python
1  group-anagrams  (medium · arrays-hashing)  weakest pattern: arrays-hashing (0.75)
   stub       python/practice/group_anagrams.py
   statement  .statements/group-anagrams.md
2  lru-cache  (medium · linked-list)  weakest pattern: linked-list (0.75)
   stub       python/practice/lru_cache.py
   statement  .statements/lru-cache.md
locked     cstudy hint and cstudy solution, until the timer ends or every problem is done
next       cstudy test group-anagrams --watch
```

An item shows `notes` and `prompt` lines instead, and the header names the language only when a problem is picked. With `open_on_start`, one editor call opens every file. Nothing in scope prints `no new medium or hard problems in scope` and starts nothing. Exit 0, or 3 while a mock runs.

## cstudy export

```text
cstudy export [--out PATH]
```

Writes every `progress.db` table but `meta` as JSON (`submissions` and `level_unlocks` included), for backup (PRD Q2): `progress-export.json` at the workspace root by default, which the user may commit; a relative `--out` is relative to the current directory, and an existing file is replaced. Rows keep their ids and their stored values (the JSON columns of `bench_runs` stay strings), in insertion order, one row per line so a committed export diffs by row. [`cstudy import`](#cstudy-import) restores it.

```json
{
  "format": "coding-study-progress",
  "version": 1,
  "schema_version": 3,
  "exported_at": "2026-10-24T10:00:00+00:00",
  "tables": {
    "attempts": [
      {"id": 1, "slug": "two-sum", "lang": "python", "mode": "new", "status": "passed", "...": "..."}
    ],
    "test_runs": [],
    "schedule": [],
    "bench_runs": []
  }
}
```

```text
$ cstudy export
exported  attempts 6 · test_runs 4 · schedule 3 · bench_runs 3
file      progress-export.json
```

`schema_version` is the last migration applied to the database. A directory that does not exist exits 3. Exit 0.

## cstudy import

```text
cstudy import [PATH]
```

Restores a `cstudy export` file (default: `progress-export.json` at the workspace root) into a `progress.db` without progress: every row with its id, in one transaction, so `cstudy stats` afterwards prints what it printed where the export was made. An export from an older schema imports as long as the later migrations only add tables, or columns with defaults.

```text
$ cstudy import
imported  attempts 6 · test_runs 4 · schedule 3 · bench_runs 3
into      progress.db
```

Exits 3, importing nothing, when the database already holds an attempt, test run, schedule entry, bench run, submission or level unlock (merging is [PRD Q12](../prd.md#8-open-questions)), when the file is missing, not JSON or not an export, when its `schema_version` is newer than this `cstudy`, or when a table, column or row does not fit the schema. Exit 0 otherwise.

## cstudy serve

```text
cstudy serve [--port N] [--open]
```

Serves the local web UI for the workspace on `127.0.0.1` until stopped ([web-ui](web-ui.md), [ADR 0015](../decisions/0015-local-web-ui.md)). The page runs the practice loop through the same use cases and commands as the terminal.

| Flag | Effect |
|------|--------|
| `--port N` | Listen on `127.0.0.1:N`, 1 to 65535; default 0, a free port the system picks |
| `--open` | Open the page in the default browser, through a redirect file so the token stays out of other processes' arguments ([security](web-ui.md#security)); without it no browser opens |

```text
$ cstudy serve --open
cstudy serve 0.9.0 · workspace ~/cstudy-workspace
open       http://127.0.0.1:53817/?token=QmFua1Byb2plY3Q...
run        submit bank-project-python · failed · 9/10 · 1.4s
run        test two-sum · kotlin · passed · 14/14 · 2.1s
job        doctor --fix · exit 0
stop       Ctrl-C
```

| Rule | Detail |
|------|--------|
| Workspace | Needed, as for every practice command: exit 3 without one |
| Address | `127.0.0.1` only; there is no option to bind another address |
| Output | The version and workspace, the URL with its session token once, then one line per finished run and job; no request log. The token is printed nowhere else |
| Stop | Ctrl-C (SIGINT) or SIGTERM sends SIGINT to every run and job in progress, closes the streams, removes the redirect file and exits 130 (143 after SIGTERM) |
| Exit 4 | The port is in use (`port 53817 on 127.0.0.1 is already in use; choose another with --port`), or the web server libraries or the page's assets are missing or do not match their manifest (`fix: reinstall cstudy`); `cstudy doctor` shows both as `WARN` rows |
| Import cost | Only `cstudy serve` imports the web server, so every other command starts as before (NFR-2) |
