# Test gate lanes

`lanes.sh` runs the whole pytest suite as four disjoint lanes, so that every test runs exactly once and the slow lanes can run side by side.

| Lane | Selects | Notes |
|------|---------|-------|
| `fast` | `-m "not slow"` | Runs first and alone, with its `--basetemp` on `/dev/shm/cs-fast` |
| `slow-core` | `-m "slow and not docker"`, without the browser test files | Gradle, Node, tsc and workspace venvs |
| `browser` | `tests/entrypoints/web/test_browser_*.py` | Only the Playwright engines installed under `~/.cache/ms-playwright` |
| `docker` | `-m docker`, without the browser test files | Needs a Docker engine; includes `docker_jvm` and `docker_go` |

`slow-core`, `browser` and `docker` start together once `fast` passes.

## Run

```bash
tools/gate/lanes.sh                       # all four lanes
tools/gate/lanes.sh fast                  # only the named lanes (fast still goes first)
tools/gate/lanes.sh --no-stop             # run the other lanes even when fast fails
tools/gate/lanes.sh --collect-check       # prove the lanes are disjoint and cover the suite
tools/gate/lanes.sh fast -- -k test_user_docs   # arguments after -- go to every lane
```

| Flag | Meaning |
|------|---------|
| `--logs DIR` | Write logs under `DIR`; the default is a new `cs-gate-logs-<timestamp>` directory under `${TMPDIR:-/tmp}` |
| `--no-stop` | Run `slow-core`, `browser` and `docker` even when `fast` fails |
| `--collect-check` | Collect each lane and the full suite, and compare the node ids; runs no tests, exits non-zero on an overlap or a gap |
| `-- ARGS` | Extra pytest arguments for every lane. A lane's own arguments come first, so a `-k` passed here replaces the browser lane's engine filter |
| `CS_LANE_ARGS_<LANE>` | Environment variable with extra arguments for one lane (`FAST`, `SLOW_CORE`, `BROWSER`, `DOCKER`) |

Run `--collect-check` after adding a marker or moving a test file. It collects the suite once per lane in parallel and takes a few minutes.

## Output

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
