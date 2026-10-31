# Spec: CLI (`cstudy`)

`cstudy` is the only interface. It is installed as a tool with its content bundled, and every command runs against a content root (problems, tracks, runners, schemas) and a workspace (your practice projects, notes and progress); [installation-and-workspaces](installation-and-workspaces.md) defines how both are found. Paths `cstudy` prints for workspace files are relative to the workspace root.

## Command summary

| Command | Purpose | Phase |
|---------|---------|-------|
| [`cstudy init`](installation-and-workspaces.md#cstudy-init) | Create a workspace | W1 |
| [`cstudy doctor`](#cstudy-doctor) | Check and set up toolchains | 0 |
| [`cstudy ide`](#cstudy-ide) | Write or refresh the VS Code and IntelliJ project files | W1 |
| [`cstudy start`](#cstudy-start) | Create or reopen a stub, open the statement, begin an attempt | 0 |
| [`cstudy test`](#cstudy-test) | Run the user's code against the cases; for a project problem, its native tests | 0 |
| [`cstudy submit`](#cstudy-submit) | Grade a project problem and open its next level | 8 |
| [`cstudy status`](#cstudy-status) | Show where a project attempt stands | 8 |
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

[`start`](#cstudy-start), [`test`](#cstudy-test), [`submit`](#cstudy-submit), [`status`](#cstudy-status), [`hint`](#cstudy-hint), [`solution`](#cstudy-solution), [`done`](#cstudy-done), [`show`](#cstudy-show) and [`bench`](#cstudy-bench) take the problem as `<slug>` or as the path of one of your solution files, so an IDE can run any command on the file in its editor: `cstudy test python/practice/two_sum.py` is `cstudy test two-sum --lang python`.

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
| `--json` | Machine-readable output, as an option of the command (`cstudy stats --json`, not `cstudy --json stats`): `stats`, [`test`](#json-output), [`submit`](#cstudy-submit) and [`status`](#cstudy-status) have it; `list`, `next`, `bench` and `verify` do not yet |
| `--events` | The run as a stream of JSON events instead of the report, as an option of the command: [`test`](#project-problems) on a project problem and [`submit`](#cstudy-submit) have it ([Event stream](#event-stream)) |
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
cstudy doctor [--fix]
```

Checks Python 3.13, uv, Node 24 or newer, pnpm, JDK 21, Homebrew Gradle, Go 1.24 or newer, `rustc` 1.80 or newer and `cargo` (the Go and Rust toolchains are optional, so these three rows WARN, never FAIL, with a link to the [toolchains guide](../guides/toolchains.md)), Delve (`dlv`, found as [debug mode](runners.md#debug-mode) finds it; the row shows its version, and a release other than the tested 1.27.2 passes with `(cstudy is tested with 1.27.2)`) and Rust's debug server (`debugserver` on macOS, `lldb-server` on Linux; the row shows its path), which only `cstudy test --debug` needs, so they WARN too, with the install step and the guide (``needed for --debug with --lang go, run `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`: <guide>#go``), the config file, the content root, the workspace (core template files FAIL when missing, the optional `go.work`, `go/` and `rust/` files WARN; [workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)), the Gradle wrapper, the workspace venv, `debugpy` and `pytest` in it, the `.venv` links of the Python project folders, the `go.work`, `replace` lines and module paths of the Go project folders, the `.cargo/config.toml` and rust-analyzer link of the Rust ones, the libraries that Java and Kotlin project folders build with offline ([workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)), `node_modules`, and that the runner of each core language (`python`, `typescript`, `java`, `kotlin`; the Go and Rust runners are not handshaken, since that would compile them) answers `hello`: the runner is prepared for a problem with no files (`cs-doctor-handshake`, so the JVM build compiles no practice code) and started with no jobs. Outside a workspace only the toolchains, the config and the content are checked. `--fix` first writes every missing workspace template file (never overwriting one) and refreshes the runner runtime, then runs, in each workspace project that exists, `uv sync` in `python`, `pnpm install` in `typescript` (and, when the content is a checkout, in its `runners/typescript` for the runner's own `tsc` and Node types), and in `jvm` the Gradle warm-up: `./gradlew :java:csClasspath :kotlin:csClasspath -Pcs.only=cs_doctor_handshake` (builds the runner and support classes, resolves the runtime classpath so that the runner's own libraries are cached for offline builds, and warms the daemon without compiling practice files), then `./gradlew -p ../.cs/runtime/runners/jvm/project-warmup/java -q --console=plain csClasspath` and the same for `kotlin` (the warm-up projects, which cache what Java and Kotlin project folders build with: [JVM project folders](installation-and-workspaces.md#jvm-project-folders)), printing one line per command and the last 10 output lines of a failed one. `--fix` outside a workspace exits 3.

| Status | Meaning |
|--------|---------|
| `ok` | Check passed |
| `WARN` | Not blocking: Homebrew Gradle missing (only needed to regenerate the wrapper), no workspace yet, a workspace project not set up yet, or `debugpy` missing from an existing venv (only [`cstudy test --debug`](#cstudy-test) needs it; `fix: uv add --dev debugpy --directory python`, which also covers a workspace created before the template listed it); `pytest` missing from it (only Python project problems need it; `fix: uv add --dev pytest --directory python`); no `projects/` folder; a dangling `.venv` link in a project folder, a `python/.venv` that moved, or Java or Kotlin project libraries not cached yet (all under [workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)); Go, Rust, Delve or Rust's debug server missing (only `--lang go`, `--lang rust` or their `--debug` needs them) |
| `FAIL` | Blocks practice; a `fix:` hint follows when one applies |

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

## cstudy ide

```text
cstudy ide [vscode|idea|all] [--force]
```

Writes or refreshes the workspace's [IDE files](installation-and-workspaces.md#ide-files) (`.vscode/`, `.idea/`) for the named IDE (default: `all`), and installs the IntelliJ launcher into `.cs/runtime/ide/`. VS Code's `rust-analyzer.linkedProjects` lists the Rust project folders that exist when it runs, so run it again after starting a Rust project problem. `cstudy init` does the same unless `--no-ide`; `--ide vscode` or `--ide idea` (repeatable) limits it to those.

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
| `--json` | One [JSON document](#json-output) on standard output instead of the report; with `--watch`, `--perf` or `--debug` it is a usage error |
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
| `--events` | The run as an [event stream](#event-stream) instead of the report; on a problem of another kind it exits 3 |
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
| Origin | A test in a generated file of an unlocked level is untagged; a test in a file the problem's `starter/` holds is tagged `starter`, any other `yours` |
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

`--json` prints one document in the style of [`cstudy test --json`](#json-output): `slug`, `language`, `attempt_id`, `mode`, `outcome` (`passed`, `failed` or `load_failed`), `exit_code`, `every_level` (whether it graded every unlocked level), `timer`, `levels` (`graded_up_to`, `last`, `unlocked`, `newly_unlocked`, and `methods_added`, the methods of a newly opened level in the language's names, else empty), `level_tallies` (per level: `level`, `total`, `passed`, `visible_total`, `visible_passed`, `hidden_total`, `hidden_passed`), `load_error`, `diagnostics` (the [diagnostics](#diagnostics) of code that did not load, else empty), `cases` (as in `cstudy test --json`, each with its `level`; in a mock attempt hidden cases are left out and only `level_tallies` counts them), `tally` and `duration_s`.

`--events` writes the submission as an [event stream](#event-stream) instead of the report.

## Event stream

`cstudy test --events` on a [project problem](#project-problems) and `cstudy submit --events` write the run as a stream of events instead of the report: newline-delimited JSON on standard output, one object per line, each line written and flushed as soon as `cstudy` has it. It is the boundary a web interface builds on to show a run as it happens ([ADR 0014](../decisions/0014-project-problems.md)). `schemas/events.schema.json` describes every event.

```text
$ cstudy submit --events
{"type": "run_start", "version": 1, "command": "submit", "slug": "bank-project-python", "language": "python", "attempt_id": 7, "mode": "new", "levels": {"up_to": 1, "unlocked": 1, "last": 4}}
{"type": "case_result", "version": 1, "id": "ex1", "visible": true, "generated": false, "status": "pass", "duration_ns": 41000, "level": 1}
{"type": "case_result", "version": 1, "id": "h1", "visible": false, "generated": false, "status": "fail", "duration_ns": 38000, "input": {"ops": ["Bank", "create_account"], "args": [[], [1, "zoe"]]}, "expected": [null, true], "actual": [null, false], "reason": null, "level": 1}
{"type": "level_result", "version": 1, "status": "fail", "level": 1, "total": 2, "passed": 1, "visible_total": 1, "visible_passed": 1, "hidden_total": 1, "hidden_passed": 0}
{"type": "run_end", "version": 1, "outcome": "failed", "exit_code": 1, "message": null, "summary": {"slug": "bank-project-python", ...}}
```

| Rule | Detail |
|------|--------|
| Lines | Every line is one JSON object whose first fields are `type` and `version`. Standard output holds nothing else; `error: ...` goes to standard error, as for any command |
| Version | `version` is 1. It changes only when an event changes incompatibly: a field removed, renamed or given another type, or an ordering rule dropped. New event types and new fields keep the version, so a reader ignores the types and fields it does not know |
| `--json` | A final summary, where events are a stream: `run_end` carries the document `--json` prints, so the two flags exclude each other (`--events excludes --json`, exit 3) |
| Excluded | `--watch` and `--debug` exit 3 (`--events excludes --watch`); `cstudy test --events` on a problem of another kind exits 3 (`--events is for project problems`) |
| Exit codes | Those of the run without `--events`; `run_end.exit_code` is the exit code of the process |

### Events

| `type` | Command | Fields | When |
|--------|---------|--------|------|
| `run_start` | both | `command` (`test` or `submit`), `slug`, `language`, `attempt_id`, `mode` (`new`, `review` or `mock`), `levels`: `up_to` (the last level the run covers), `unlocked` and `last` | Once the options are checked, before the run's work begins |
| `output` | both | `text`: a progress notice the report would print, such as `computing expected values ...` | As it happens |
| `test_start` | `test` | `id`: the test id, as in `test_result` | As the runner starts the test, a test file it collects included |
| `test_result` | `test` | An entry of `cases` in [`cstudy test --json`](#project-problems) on a project problem: `id`, `status`, `duration_ns`, `origin`, `level`, and `message`, `expected`, `actual`, `error` and `stdout` when set | As the test ends: once per test the suite reported, a test file that failed to collect included |
| `case_start` | `submit` | `id`, `visible` and `level` of the case | As the runner starts the case; a mock attempt writes none for hidden cases |
| `case_result` | `submit` | An entry of `cases` in [`cstudy submit --json`](#cstudy-submit), with its `level` | As the case ends and is judged: once per graded case; a mock attempt writes none for hidden cases, which only `level_result` counts |
| `diagnostic` | both | One [diagnostic](#diagnostics) | Once per diagnostic |
| `level_result` | `submit` | An entry of `level_tallies` in `cstudy submit --json`, plus `status`: `pass` when every graded case of the level passed, else `fail` | Once per graded level |
| `level_unlocked` | `submit` | `level`, `title`, `methods` (the methods the level adds, in the language's names, as `methods_added`), `tests` (`path` of the level's generated test file relative to the project folder, and `count`, its tests) and `statement` (the rewritten statement's path) | When the submission opened a level |
| `run_end` | both | `outcome`, `exit_code`, `message` and `summary` | Last |

`run_end.outcome` is the `outcome` of the `--json` document (`passed`, `failed`, `build_failed` or `load_failed`), `error` when the run stopped after `run_start` (an environment error such as pytest missing from `python/.venv`, a `--case` that names no test, an internal error), or `interrupted` (Ctrl-C, exit 130). `summary` is the document `--json` prints, or null for `error` and `interrupted`; `message` is the error's text for `error`, else null.

### Ordering

| Rule | Detail |
|------|--------|
| Bounds | `run_start` is the first line and `run_end` the last. A run that stops before it starts (no attempt, a locked level, another kind of problem) writes no event, only `error: ...` on standard error, as `--json` writes no document. Once `run_start` is written, `run_end` follows unless the process is killed |
| Output | `output` may come anywhere between `run_start` and `run_end` |
| Results | `test_result` and `case_result` come in run order: the suite's order for tests, `tests.json` order for cases. A start comes before the result of its test or case, and no other test's or case's event comes between them. A result comes without a start when the runner never started its test or case: a hang or crash between cases is recorded on the next case, and a case left not run when restarts ran out comes, with status `not_run`, after the results the runner reported |
| Diagnostics | `diagnostic` comes after `run_start` and before the first `level_result`, or before `run_end` in `cstudy test` |
| Levels | `level_result` comes after every `case_result`, in level order, then `level_unlocked` |
| Timing | Each start and result is written as the runner reports it, while the run goes on, so a reader can show the test in progress. A result that ended in a hang is written when the hang guard expires. The time between a start and its result includes the runner's own work; `duration_ns` is the test's or call's duration |

### Diagnostics

A diagnostic says where code does not load, build or type-check, so an editor can mark the place.

| Field | Meaning |
|-------|---------|
| `source` | `load` (the runner could not load the code, or the framework could not collect a test file), `typecheck` (a type checker, such as `tsc --noEmit` for `--typecheck`) or `build` (a compiler) |
| `severity` | `error`, `warning` or `info` |
| `file` | Relative to the project folder, or null when the report names no file |
| `line`, `column` | 1-based, or null when the report names none; a runner's trace never names a column |
| `code` | The tool's name for the problem: the exception type (`SyntaxError`, `SymbolNotFound`) or a compiler's code (`TS2322`); null when it has none |
| `message` | The tool's message; the exception type when the message is empty |

A `load` diagnostic comes from a [load error](runners.md#event-stream---out-json-lines):

| Load error | Where it points |
|------------|-----------------|
| The grading job's, or a test file that failed to collect (a result whose id is the file, which stays a `test_result` with status `error` as well) | The innermost frame of the error's trace: `bank/bank.py:12 in Bank.deposit` gives `bank/bank.py`, line 12. `code` is the error's type |
| The suite's own, when the framework refused to run it, such as a `conftest.py` that does not import | Read from the framework's report: the innermost frame of its Python traceback that lies in the project folder, an absolute path made relative to the folder, and the traceback's last exception as `code` and `message` (`E   SyntaxError: invalid syntax`) |

Diagnostics are `diagnostic` events, and the `diagnostics` list of `cstudy test --json` on a project problem and of `cstudy submit --json`. An error without such a frame gives a diagnostic without a place, and one without an exception line keeps its own type and message. Test files that fail on the same line of one module give one diagnostic. An exception a test raises while it runs is a test result, not a diagnostic. A type checker's or compiler's report is read by a parser for its format into the same fields. For `tsc`, each line `src/bank.ts(3,5): error TS2322: <message>` is one diagnostic, with its category (`error`, `warning`, or `message` and `suggestion` as `info`) as `severity`, its code as `code`, and the indented lines below it continuing `message`; a path outside the project folder is given from the folder (`../../typescript/support.ts`), and a line without a place, such as `error TS5083: ...`, has none. A checker without a parser gives each line as a diagnostic without a place.

## cstudy status

```text
cstudy status [<slug|file>] [--json]
```

Shows where a [project problem](problem-format.md#project-problems)'s attempt in progress stands, without running anything.

| Line | Content |
|------|---------|
| Header | Slug, language, `project`, attempt id and mode |
| `level` | The unlocked level, of the last, with its title and when it opened |
| `timer` | Elapsed and time box, with `--timer`; else absent |
| `tested` | The latest `cstudy test`: passed of total, and how long ago. A run older than a level's opening covered none of that level's tests, so the line then ends with the first level that opened after it: `2/2 passed, 12 min ago, before level 2 opened` |
| `submitted` | The latest submission's tally per level, and how long ago; `best` adds the highest passed count per level over the attempt when it differs |
| `files` | Starter files changed and removed, and files added, under `projects/<slug>/`, by content against what the starter provided (the folder's [manifest](installation-and-workspaces.md#project-folders)); generated test files, `.venv` and caches are left out |
| `next` | `cstudy test --watch` before any submission, `cstudy submit once level <n> passes`, or `cstudy done --rating easy\|ok\|hard` after the full pass |

```text
$ cstudy status
bank-project-python · python · project · attempt 41 · new
level      2 of 4: Top spenders (opened 18:02)
timer      33:05 / 90:00
tested     3/4 passed, 1 min ago
submitted  level 1 5/5 · level 2 4/5, 2 min ago
files      2 changed, 1 added, 0 removed against the starter
next       cstudy submit once level 2 passes
```

`--json` writes the same values: `slug`, `language`, `attempt_id`, `mode`, `statement` (its path), `levels` (`unlocked`, `last`, `titles` of the open levels, `opened_at` per open level), `timer`, `last_test_run` (`ran_at`, `total`, `passed` and `predates_level`, the first level that opened after the run or null, or null without a run), `latest_submission` (`submitted_at`, `level_tallies`, or null), `best_per_level` (`level`, `passed`, `total`), `files` (`changed`, `added`, `removed`, each a sorted list of paths relative to the folder, and `entries`, below) and `next`. In a mock attempt the tallies count hidden cases but name none.

`files.entries` is the folder's tree for an interface that shows it: every file under the folder, untracked ones aside, and every file `cstudy` provided that the folder lacks, in path order, each with `path` (relative to the folder), `origin`, `level` and `state`.

| `origin` | `level` | `state` |
|----------|---------|---------|
| `starter`: a file the starter provided | null | `unchanged` while its content is what `cstudy` provided, `modified` once it differs, `deleted` when the folder lacks it |
| `level`: the [generated test file](problem-format.md#generated-test-files) of an open level | its level | the same: `modified` is a test file you edited |
| `yours`: any other file | null | `added` |

Without a manifest (a folder started before `cstudy` kept one, or a clone), `status` compares the folder with what `cstudy` provides now: the starter and the generated test files of the open levels. It writes no manifest; the next `cstudy start` does.

Exit 0; 3 without an attempt in progress, or for a problem of another kind (`cstudy status is for project problems`).

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
cstudy next [--track T]... [--pattern P] [--difficulty D] [--lang L] [--new | --review] [--start]
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

## cstudy list

```text
cstudy list [--track T] [--pattern P] [--difficulty D] [--status S] [--content draft|ready] [--lang L]
```

`--status`: `new`, `attempted`, `passed`, `due`, `mastered` (definitions in [progress-and-scheduling](progress-and-scheduling.md#problem-status)). `--lang` filters to problems whose references cover that language. Non-autograded items follow the problems, ordered by track, `order` and slug, with `-` for the id and the references and their track in the pattern column; `--pattern` and `--lang` leave them out.

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
| `--ladder` | Bench references and check time bands against declared classes: one language at a time after the parallel checks, only where the references passed their cases, memory off, `perf.size_ladder` sizes. Prints `ladder ok` or `ladder FAIL`; a reference with fewer than 3 usable sizes is a warning, not a failure. A problem without `generator.py` prints `ladder n/a` and does not fail |
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
