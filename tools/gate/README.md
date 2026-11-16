# Release gate scripts

The release gate has two halves: `lanes.sh` runs the pytest suite, and `verify.sh` runs `cstudy verify` over the catalog content. Both run every check once, in concurrent parts, and write one summary line per part.

## Test lanes

`lanes.sh` runs the whole pytest suite as four disjoint lanes, so that every test runs exactly once and the slow lanes can run side by side.

| Lane | Selects | Notes |
|------|---------|-------|
| `fast` | `-m "not slow"` | Runs first and alone, with its `--basetemp` on `/dev/shm/cs-fast` |
| `slow-core` | `-m "slow and not docker"`, without the browser test files | Gradle, Node, tsc and workspace venvs |
| `browser` | `tests/entrypoints/web/test_browser_*.py` | Only the Playwright engines installed under `~/.cache/ms-playwright` |
| `docker` | `-m docker`, without the browser test files | Needs a Docker engine; includes `docker_jvm` and `docker_go` |

Lanes run in this order: `fast` alone, then `browser` alone, then `slow-core` and `docker` together. `browser` runs alone because Docker's network changes cancel Chromium's requests (`net::ERR_NETWORK_CHANGED`). A failed lane skips the later ones unless `--no-stop` is given.

### Run

```bash
tools/gate/lanes.sh                       # all four lanes
tools/gate/lanes.sh fast                  # only the named lanes, still in that order
tools/gate/lanes.sh --no-stop             # run the later lanes even when an earlier lane fails
tools/gate/lanes.sh --collect-check       # prove the lanes are disjoint and cover the suite
tools/gate/lanes.sh fast -- -k test_user_docs   # arguments after -- go to every lane
```

| Flag | Meaning |
|------|---------|
| `--logs DIR` | Write logs under `DIR`; the default is a new `cs-gate-logs-<timestamp>` directory under `${TMPDIR:-/tmp}` |
| `--serial` | Run every lane without pytest-xdist workers |
| `--no-stop` | Run the later lanes even when an earlier lane fails |
| `--collect-check` | Collect each lane and the full suite, and compare the node ids; runs no tests, exits non-zero on an overlap or a gap |
| `-- ARGS` | Extra pytest arguments for every lane. A lane's own arguments come first, so a `-k` passed here replaces the browser lane's engine filter |
| `CS_LANE_ARGS_<LANE>` | Environment variable with extra arguments for one lane (`FAST`, `SLOW_CORE`, `BROWSER`, `DOCKER`) |
| `CS_LANE_XDIST_<LANE>` | Environment variable that replaces one lane's xdist arguments; set it empty to run that lane serially |

### Parallel workers

Each lane runs on pytest-xdist workers:

| Lane | Default arguments | Why |
|------|-------------------|-----|
| `fast` | `-n 4` | Independent tests |
| `slow-core` | `-n 2 --dist loadfile` | A module's shared workspace copy stays on one worker |
| `browser` | `-n 2 --dist loadfile` | One module's browser and server stay on one worker |
| `docker` | none | Serial |

```bash
tools/gate/lanes.sh --serial                          # no workers in any lane
CS_LANE_XDIST_FAST="-n 8" tools/gate/lanes.sh fast   # another worker count for one lane
CS_LANE_XDIST_SLOW_CORE= tools/gate/lanes.sh slow-core   # one lane serial
```

`--collect-check` never passes `-n`.

Run `--collect-check` after adding a marker or moving a test file. It collects the suite once per lane in parallel and takes a few minutes.

### Output

Everything goes under the logs directory; the repository gets only `cli/.pytest_cache/<lane>/` (ignored).

| File | Content |
|------|---------|
| `summary.log` | One line per lane: name, exit code, wall time, pytest's final result line. Read this first |
| `<lane>.log` | The lane's full pytest output, with `--durations=50 --durations-min=5` |
| `<lane>.xml` | The lane's JUnit XML, with per-test times |
| `sync.log` | The environment sync |
| `collect/` | With `--collect-check`: node ids per lane and the overlap, missing and extra lists |

The script exits non-zero when any lane failed. Each lane has its own `--basetemp` and its own pytest cache directory. A lane that passes deletes its temporary directory; a failed lane keeps it and `summary.log` names the path. The `fast` lane refuses to start when `/dev/shm` has under 4 GB free. When some Playwright engines are not installed, `summary.log` lists the ones skipped.

The script runs `uv sync --locked --group browser` once and every lane through `uv run --no-sync`: a plain `uv run` would sync the environment back to the default groups and uninstall `browser` under a running browser lane.

## Content verify

`verify.sh` runs the content half of the gate: `cstudy verify --require-ready` over every problem, `cstudy verify --conformance --require-ready` and both tracks. One `cstudy verify` process over the whole catalog is too slow, so the problems are split into groups that run as concurrent processes on one workspace. That is safe because every process writes its run folders under its own name.

| Part | Runs |
|------|------|
| `static` | `cstudy verify --static`, first and alone; a failure skips the rest unless `--no-stop` is given |
| `ordinary` | every problem that is not a service project |
| `services-a`, `services-b` | the service projects with backing services, in two halves |
| `services-other` | the other service projects |
| `conformance`, `track-system-design`, `track-code-review` | one after the other, beside the four groups above |

A service project is a problem whose `meta.yaml` has `grading: http` under `project:`; it has backing services when its directory also has a `services/` folder. The script reads those two facts from the files, so a new service project lands in the right group without an edit.

```bash
export CSTUDY_WORKSPACE=~/cstudy-dev-workspace
tools/gate/verify.sh                                 # all parts
tools/gate/verify.sh --workspace ~/cstudy-gate --fresh   # create the workspace first
tools/gate/verify.sh --list                          # print each group with its slug count; runs nothing
```

| Flag | Meaning |
|------|---------|
| `--workspace DIR` | The workspace to verify in; the default is `$CSTUDY_WORKSPACE` |
| `--fresh` | Run `cstudy init DIR --no-ide` and `cstudy doctor --fix` first |
| `--logs DIR` | Write logs under `DIR`; the default is a new `cs-verify-logs-<timestamp>` directory under `${TMPDIR:-/tmp}` |
| `--no-stop` | Run the later parts even when `static` fails |
| `--no-recheck` | Do not rerun failures alone; any failed part fails the gate |
| `--list` | Print the groups and exit |

### Recheck

Concurrency problems have load-sensitive checks: a deliberately broken solution must be caught in at least 9 of 10 stress runs, a conformance fixture's stress case has the same bound, and a suite case can time out. The concurrent parts load the machine, so these checks can fail there and pass when rerun alone.

When a part fails, the script reads its log, collects the problems and conformance fixtures whose line is `FAIL` or `not ready`, and reruns only those once, serially and alone, after every part has finished:

| Failed part | Rerun as | Command |
|-------------|----------|---------|
| `ordinary`, `services-a`, `services-b`, `services-other` | `recheck-problems` | `cstudy verify --require-ready --jobs 1 <problems>` |
| `conformance` | `recheck-conformance` | `cstudy verify --conformance --require-ready --jobs 1 <fixtures>` |
| `track-system-design`, `track-code-review` | `recheck-track-<track>` | `cstudy verify --track <track> --require-ready --jobs 1` |

The problem table truncates long names with `...`; the script maps each to the problem directory it is a prefix of. Each recheck part has its own log, which starts with the 1-minute load average, and its own summary line.

The gate passes when every recheck passes. The original failing lines stay in `summary.log`, followed by a `gate: PASSED ON RECHECK` line that names the parts that failed first. A failure the script cannot map to a problem or fixture (including a `static` failure under `--no-stop`) is not rerun and fails the gate. `--no-recheck` disables the rerun.

`summary.log` has one line per part: name, exit code, wall time and cstudy's final `result` line; `<part>.log` holds the full output. The script exits non-zero when a part failed and its recheck did not pass. Every call is `uv run --no-sync cstudy`, because a plain `uv run` would sync the environment back to the default groups.
