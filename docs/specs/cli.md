# Spec: CLI (`cstudy`)

`cstudy` is the only interface. It is installed as a tool with its content bundled, and every command runs against a content root (problems, tracks, runners, schemas) and a workspace (your practice projects, notes and progress); [installation-and-workspaces](installation-and-workspaces.md) defines how both are found. Paths `cstudy` prints for workspace files are relative to the workspace root.

## Command summary

| Command | Purpose | Phase |
|---------|---------|-------|
| [`cstudy init`](installation-and-workspaces.md#cstudy-init) | Create a workspace | W1 |
| [`cstudy doctor`](#cstudy-doctor) | Check and set up toolchains | 0 |
| [`cstudy ide`](#cstudy-ide) | Write or refresh the VS Code and IntelliJ project files | W1 |
| [`cstudy start`](#cstudy-start) | Create or reopen a stub, open the statement, begin an attempt | 0 |
| [`cstudy test`](#cstudy-test) | Run the user's code against the cases | 0 |
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

[`start`](#cstudy-start), [`test`](#cstudy-test), [`hint`](#cstudy-hint), [`solution`](#cstudy-solution), [`done`](#cstudy-done), [`show`](#cstudy-show) and [`bench`](#cstudy-bench) take the problem as `<slug>` or as the path of one of your solution files, so an IDE can run any command on the file in its editor: `cstudy test python/practice/two_sum.py` is `cstudy test two-sum --lang python`.

| Rule | Detail |
|------|--------|
| Path or slug | An argument is a path when it contains `/` or `\`, or ends in `.py`, `.ts`, `.java` or `.kt`; anything else is a slug or an id, even when a file of that name exists. Relative paths resolve against the current directory, so an IDE passes the absolute path of the open file |
| Files | The files [`cstudy start`](#cstudy-start) writes ([layout](../architecture.md#repository-layout)): `python/practice/<snake_slug>.py`, `typescript/practice/<slug>.ts`, and `jvm/<java\|kotlin>/src/main/<java\|kotlin>/practice/<snake_slug>/<File>.<java\|kt>`. On the JVM any source file directly in the problem's package counts, such as the declared class of a class-design problem or a helper class |
| Problem | The slug is the problem whose file name the path carries (`two_sum` is `two-sum`); a path that names no problem exits 3 |
| Language | The path's language is the language of the run. `--lang` may repeat it; naming another language exits 3 with both. `hint`, `done` and `show` have no `--lang`: they act on the problem, as with its slug |
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
| `--json` | Machine-readable output, as an option of the command (`cstudy stats --json`, not `cstudy --json stats`): `stats` and [`test`](#json-output) have it; `list`, `next`, `bench` and `verify` do not yet |
| `--version` | Print `cstudy <version>` (for example `cstudy 0.1.0`), read from the installed package metadata, and exit 0 ([versioning](versioning.md)) |
| `--no-color` | Plain output (also when `NO_COLOR` is set or stdout is not a TTY) |
| `-v`, `--verbose` | Planned, not implemented yet: show runner commands, build output and timings |
| `--workspace PATH` | The workspace, before the command (`cstudy --workspace ~/ws start two-sum`); overrides `CSTUDY_WORKSPACE` |
| `--content PATH` | The content root, before the command; overrides `CSTUDY_CONTENT`. Unrelated to `cstudy list --content`, which filters by content status |

## Configuration

One user-level file: `$XDG_CONFIG_HOME/coding-study/config.toml` (default `~/.config/coding-study/config.toml`); `CSTUDY_CONFIG` overrides the path. All keys are optional; defaults below. Precedence everywhere: CLI flag, then this file, then the problem's `meta.yaml`, then built-in defaults.

```toml
default_lang = "python"          # python | typescript | java | kotlin
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

Checks Python 3.13, uv, Node 24 or newer, pnpm, JDK 21, Homebrew Gradle, the config file, the content root, the workspace ([workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)), the Gradle wrapper, the workspace venv, `debugpy` in it, `node_modules`, and that the runner of each language (`python`, `typescript`, `java`, `kotlin`) answers `hello`: the runner is prepared for a problem with no files (`cs-doctor-handshake`, so the JVM build compiles no practice code) and started with no jobs. Outside a workspace only the toolchains, the config and the content are checked. `--fix` first writes every missing workspace template file (never overwriting one) and refreshes the runner runtime, then runs, in each workspace project that exists, `uv sync` in `python`, `pnpm install` in `typescript` (and, when the content is a checkout, in its `runners/typescript` for the runner's own `tsc` and Node types), and `./gradlew :java:classes :kotlin:classes -Pcs.only=cs_doctor_handshake` in `jvm` (builds the runner and support classes and warms the daemon without compiling practice files), printing one line per command and the last 10 output lines of a failed one. `--fix` outside a workspace exits 3.

| Status | Meaning |
|--------|---------|
| `ok` | Check passed |
| `WARN` | Not blocking: Homebrew Gradle missing (only needed to regenerate the wrapper), no workspace yet, a workspace project not set up yet, or `debugpy` missing from an existing venv (only [`cstudy test --debug`](#cstudy-test) needs it; `fix: uv add --dev debugpy --directory python`, which also covers a workspace created before the template listed it) |
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

Writes or refreshes the workspace's [IDE files](installation-and-workspaces.md#ide-files) (`.vscode/`, `.idea/`) for the named IDE (default: `all`), and installs the IntelliJ launcher into `.cs/runtime/ide/`. `cstudy init` does the same unless `--no-ide`; `--ide vscode` or `--ide idea` (repeatable) limits it to those.

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
cstudy start <slug|file> [--lang L] [--fresh] [--timer DURATION] [--no-open]
```

| Flag | Effect |
|------|--------|
| `--lang` | Language; default `default_lang` |
| `--fresh` | Archive the existing file and write a new stub (implied for review attempts) |
| `--timer` | Time box, for example `25m` or `1h`; shown by `cstudy test`; finishing over time caps the grade at `hard` |
| `--no-open` | Do not launch the editor |

Effects: generate or keep the stub ([runners](runners.md#stub-generation)), render `.statements/<slug>.md`, insert an attempt (`in_progress`), and open `$EDITOR <stub> <statement>`. Starting a problem that already has an `in_progress` attempt in the same language resumes it. A progressive problem's new attempt opens level 1, and the statement shows only the unlocked levels; the output adds a `level` line (`level      1 of 4: Set and get`).

```text
two-sum · easy · arrays-hashing · kotlin
stub       jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt
statement  .statements/two-sum.md
next       cstudy test --watch
```

For non-autograded items (system design, code review) `cstudy start` copies the item's `template.md`, under a header comment, to `notes/<track>/<slug>.md`, renders `prompt.md` (plus the change under review) to `.statements/<slug>.md`, inserts an attempt with no language and opens both files. `--lang` is a usage error; `--fresh` and review attempts archive the notes to `.archive/<slug>/<attempt_id>-notes/`; `--timer` is recorded but does not cap the grade. When [`study_guides.root`](#configuration) is set, the statement ends with a `## Study guides` section and the output adds a `guide` line, after `prompt`, for each referenced guide whose file exists under the root (`guide      file:///home/me/study-guides/distributed-systems-study-guide.md#databases`).

```text
url-shortener · medium · system-design · 45 min
notes      notes/system-design/url-shortener.md
prompt     .statements/url-shortener.md
next       answer in the notes, then cstudy solution url-shortener
```

## cstudy test

```text
cstudy test [<slug|file>] [--lang L] [--watch] [--case ID]... [--all] [--level N]
        [--time-limit[=VALUE] | --no-time-limit] [--perf] [--typecheck] [--stress N] [--seed S]
        [--json] [--debug [--debug-port N] [--debug-connect]]
```

| Flag | Effect |
|------|--------|
| `--watch` | Re-run on save of the user file (JVM: the problem's package directory), 150 ms debounce, screen cleared each run |
| `--case` | Run only these case ids |
| `--all` | Print every case, including passing hidden ones |
| `--level` | Progressive: run levels 1 to N; N above the unlocked level exits 3 (`level 3 is locked; pass level 2 with cstudy test first`), as does `--level` on a problem without levels |
| `--time-limit[=VALUE]` | Enable time limits; optional VALUE `5x` or `1500ms` ([precedence](performance-analysis.md#precedence)). The value only follows `=`: in `cstudy test --time-limit two-sum`, `two-sum` is the slug |
| `--no-time-limit` | Disable time limits even if config enables them; together with `--time-limit` it is a usage error |
| `--perf` | After all cases pass (not with `--case`), run a short bench (`reps` 3, stored in `bench_runs`) and print its verdict line and warnings; a wrong answer on a bench input prints `FAIL      wrong answer at n=...` and exits 1 |
| `--typecheck` | TypeScript: also run `pnpm exec tsc --noEmit` (type stripping does not type-check) |
| `--stress N` | 1 to 100. Concurrent problems: run every stress case N times per variant instead of `concurrency.runs` (default 3). Function and design problems: also run N [oracle inputs](#oracle-inputs), generated inputs checked against the oracle approach; progressive problems, and problems without `generator.py` or a Python oracle, exit 3 |
| `--seed S` | Concurrent problems: base seed of every selected stress case instead of its `seed`; run `r` uses `S + r`. In the `async` model this reproduces a reported failing run exactly (`--case s1 --seed 1007 --stress 1`). Other problems: the first oracle input's seed (default 1), so `--stress 1 --seed 17` reruns `oracle-17`; without `--stress` it exits 3 |
| `--json` | One [JSON document](#json-output) on standard output instead of the report; with `--watch`, `--perf` or `--debug` it is a usage error |
| `--debug` | Start the runner under the language's debug agent and wait for an IDE to attach to it, with every time limit off ([Debugging](#debugging)) |
| `--debug-port N` | With `--debug`: the agent's port, 1 to 65535. Defaults: Python 5678, TypeScript 9229, Java and Kotlin 5005 |
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

The ready line is a stable contract: IDE tasks and run configurations match it. It is printed once, to **standard error**, as plain text on a line of its own, after the agent is bound (so the IDE can attach at once), or, with `--debug-connect`, as the JVM is started:

```text
cstudy: waiting for debugger on 127.0.0.1:5678 (python)
cstudy: waiting for debugger on 127.0.0.1:9229 (typescript)
cstudy: waiting for debugger on 127.0.0.1:5005 (java)
cstudy: connecting to debugger at 127.0.0.1:5005 (kotlin)
```

`cstudy: waiting for debugger on` and `cstudy: connecting to debugger at` start the two forms; the port and the language are the last fields. Every other notice of a debug run (`warming Gradle daemon`, `computing expected values`) goes to standard error too, and the report goes to standard output when the run ends.

| Rule | Detail |
|------|--------|
| One language | The language of the file, `--lang` or the active attempt, as for any run |
| Excluded | `--watch`, `--perf`, `--json`, `--stress`, `--seed` and `--time-limit` exit 3 (`--debug excludes --watch, --perf`); `--no-time-limit` is accepted. `--debug-port` and `--debug-connect` without `--debug` exit 3, as does `--debug-connect` for Python and TypeScript |
| No limits | No hello timeout, hang guard or time limit; the runner is never restarted. A concurrent problem runs its sequential cases only (`stress runs are skipped while debugging`) |
| Report | The header names the run (`two-sum · python · debug · 16 cases ...`); no durations, no `total`, no `TLE`, since pauses at breakpoints would be part of them. A pass ends with `all passed (debug run: not recorded; cstudy test records the run)` |
| Not recorded | A debug run is not stored in `test_runs`, never counts as the first pass and unlocks no level; run `cstudy test` again to record it |
| Interrupted | Ctrl-C exits 130, SIGTERM 143 and SIGHUP 129; each kills the runner's process group, so the port is free again |
| Environment errors (exit 4) | `debugpy` missing from `python/.venv` (the message gives the fix, `uv add --dev debugpy --directory python`); a port in use (`cannot debug python: port 5678 on 127.0.0.1 is already in use; stop the other debug session or choose another port with --debug-port`); no IDE listening with `--debug-connect` after 10 s (`no debugger listening on 127.0.0.1:5005; start the IDE's 'Debug JVM (listen)' configuration first`); a runner that ends before it starts the run (`the debug session ended before the run started`, with the runner's last output lines) |

#### JSON output

`cstudy test --json` prints one document per run and exits as the report would. Progress notices (`computing expected values ...`, `warming Gradle daemon ...`) go to standard error; an error that stops the run before it starts (no attempt, unknown case) prints `error: ...` and no document.

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

## cstudy hint

```text
cstudy hint [<slug|file>]
```

Prints the next unrevealed `### Hint N` from `problem.md` and increments `hints_used` on the active attempt. Prints `no more hints` when exhausted (exit 0, `hints_used` unchanged). The next hint is number `hints_used + 1`, so hints are counted per attempt. Locked (exit 3) while a [mock interview](#cstudy-mock) runs.

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

Applies the selection algorithm in [progress-and-scheduling](progress-and-scheduling.md#cstudy-next-selection). `--track` is repeatable and reaches non-autograded items, for example `cstudy next --track system-design`; their `start` line has no `--lang`. `--start` runs `cstudy start` on the result, in the `--lang` language (default `default_lang`) for a problem, and prints its report instead of the `start` line; it opens the editor when `open_on_start` is on. `--new` together with `--review`, or a `--pattern` outside the [taxonomy](content.md#pattern-taxonomy), is a usage error (exit 3).

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

Prints the rendered statement (title, metadata, sections, examples generated from visible cases, unlocked levels, and for concurrent problems the generated stress-case table; never hints). For a progressive problem the unlocked levels are those of the problem's attempt in progress, or level 1 without one; `--level N` shows levels 1 to N and follows the `cstudy test --level` rules. For a non-autograded item it prints the statement `cstudy start` would write (the prompt, the change under review and the located [study guides](content.md#study-guides)) without writing it; `--level` is a usage error.

## cstudy new

```text
cstudy new <slug> [--track T] [--from-template array|tree|design|progressive|concurrent]
              [--title TEXT] [--difficulty D] [--pattern P]
```

Creates `problems/<next id>-<slug>/` from the template `cli/src/coding_study/adapters/templates/<template>/` (package data) with `status: draft`, in the content checkout when the content is one, otherwise in the workspace's own `problems/` with ids from 5001 ([your own problems](installation-and-workspaces.md#your-own-problems)): `problem.md` (required headings with `TODO` placeholder text), `meta.yaml` (template signature), `tests.json` (one visible example; `progressive`: one per level), `generator.py`, `solutions/explanation.md` (one approach section skeleton) and an empty reference file per language. The one approach is `reference` (role `optimal`, and the oracle in the `dsa` templates), because the schema requires an `optimal` approach. Function and class names come from the slug (`max-gap`: `maxGap`, `MaxGap`).

| Template | Signature shape | Default track and primary pattern |
|----------|-----------------|-----------------------------------|
| `array` (default) | `function`, params `int[]` and `int`, returns `int` | `dsa`, `arrays-hashing` |
| `tree` | `function`, param `TreeNode`, returns `TreeNode` | `dsa`, `trees` |
| `design` | `class` with constructor and two methods, comparator `ops` | `dsa`, `arrays-hashing` |
| `progressive` | `class` with 4 levels, one method per level, comparator `ops` | `practical`, none |
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
| `--jobs` | Parallel language runners (default: number of languages) |
| `--stress N` | Concurrent problems: runs per stress case and variant for D6 and D7 (default 10); D7 requires failures in at least `ceil(0.9 * N)` runs. The line reports the fewest runs a correct reference passed (`stress 10/10`), the slowest correct run as a share of its deadline (`slowest 8%`) and the (broken reference, language, case, variant) combinations caught (`broken caught 11/11`) |

Checks are listed in [authoring](authoring.md#what-cstudy-verify-checks).

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

Stored in `bench_runs` (a user run whose code does not build or load is not stored). Exit 0 when the bench completed (any verdict), 2 if the user code does not build or load, 1 if the user code fails correctness on a bench input. Concurrent problems have no bench in v1: exit 3 (`bench is not available for concurrent problems`).

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

Writes every `progress.db` table but `meta` as JSON, for backup (PRD Q2): `progress-export.json` at the workspace root by default, which the user may commit; a relative `--out` is relative to the current directory, and an existing file is replaced. Rows keep their ids and their stored values (the JSON columns of `bench_runs` stay strings), in insertion order, one row per line so a committed export diffs by row. [`cstudy import`](#cstudy-import) restores it.

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

Exits 3, importing nothing, when the database already holds an attempt, test run, schedule entry or bench run (merging is [PRD Q12](../prd.md#8-open-questions)), when the file is missing, not JSON or not an export, when its `schema_version` is newer than this `cstudy`, or when a table, column or row does not fit the schema. Exit 0 otherwise.
