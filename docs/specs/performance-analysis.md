# Spec: Performance Analysis

`cstudy bench` runs the user's solution and every reference approach on the same generated inputs, in the same runtime, and places the user on the problem's complexity ladder with an explicit confidence level. Optional time limits reuse the same reference timings so a brute force can fail large cases, like on LeetCode, when the user asks for it.

Rationale and rejected alternatives: [ADR 0005](../decisions/0005-empirical-complexity-analysis.md); calibration of the ladder check: [ADR 0009](../decisions/0009-ladder-calibration.md).

## What it can and cannot tell

| Question | Answer quality |
|----------|----------------|
| Is my growth polynomially worse than optimal (n versus n^2)? | Reliable: log-log slopes differ by about 1 |
| Is my extra memory constant or linear? | Reliable in Python; approximate on JVM and Node |
| n versus n log n? | **Not separable by slope** (the log factor adds about 0.1 to the slope over 3 decades). Judged by the ratio to the optimal reference and its trend |
| 1 versus log n versus sqrt n? | **Not separable**: such a call takes nanoseconds to a few microseconds, and where its fresh input sits in the memory hierarchy moves the slope by up to 0.5. They share one band; telling them from linear growth is reliable |
| Is a declared class right on a ladder spanning one decade? | Only roughly: the cost per unit of growth wanders by 2 to 4 times across a ladder, so neighbouring classes (n^1.5 and n^2) are within the [drift tolerance](#ladder-check) there. Two or more decades keep the check sharp |
| How do I rank? | Against the reference ladder and against the user's own past runs. There is no crowd percentile and none is ever shown |
| Exact percentiles, cross-language comparisons | Not provided; memory metrics differ by runtime |

## Time limits

Off by default for `cstudy test`. When enabled, a case whose output is correct but whose duration exceeds the limit gets status `tle` and counts as a failure. The hang guard (default 10 s) is separate and always on.

### Precedence

| Setting | 1st (highest) | 2nd | 3rd | 4th |
|---------|---------------|-----|-----|-----|
| Enabled? | `--time-limit[=VALUE]` enables, `--no-time-limit` disables | config `time_limit.enabled` | default `false` | |
| Value | `--time-limit=VALUE` | config `time_limit.value` (unset by default) | `meta.yaml` `perf.time_limit` | built-in `5x` |

The problem file can only suggest a value; it never turns limits on. Config file: [cli](cli.md#configuration).

### Values

| Form | Example | Meaning |
|------|---------|---------|
| Factor | `5x` or `5` | Per case: `max(factor * reference_case_time, floor_ms)` |
| Absolute | `1500ms`, `1.5s` | Same limit for every case; the floor does not apply |

`floor_ms` (config `time_limit.floor_ms`, default 100) prevents noise failures on tiny cases. A case is `tle` only when its output is correct and its `duration_ns` is strictly greater than its limit; the report shows the measured time, the limit and its basis (`5x hash-map, calibrated`, `floor`, or nothing for an absolute limit). Each `test_runs` row stores the applied value (`5x`, `1500ms`) or NULL.

### Calibration

| Step | Rule |
|------|------|
| Reference | Fastest `optimal` approach that exists in the attempt's language: every such approach is measured, and the one with the smallest total of per-case medians over the cases all of them measured wins (the first in `meta.yaml` order on a tie) |
| Method | Run the references through the normal reference path 3 times (3 runner processes, cold, like the user's run; one job per approach), on every case of the problem so any `--case` selection reuses it; per-case median `duration_ns` of the calls that returned |
| When | After the user's run, only when time limits are enabled with a factor and the user's code built and loaded: the runtime version in the key is the one the runner reported in `hello` |
| Cache | `.cs/calibration/<lang>/<slug>.json` holds the latest calibration, keyed by a hash of the optimal reference files, `tests.json`, `generator.py`, the runtime version and the machine id (host name, architecture, processor, core count); any other key is a miss |
| No reference in this language | Use an absolute value if one resolves from flag, config or meta; otherwise print `time limit unavailable for <lang>: no optimal reference` and judge without limits |
| First use | Prints `calibrating time limits (one-time)` |

## Size ladder and inputs

| Item | Rule |
|------|------|
| Sizes | `perf.size_ladder` (default `[100, 1000, 10000, 100000]`), never above the problem's constraints; `--sizes` overrides |
| Inputs | One input per size from `generator.py` with seed `hash(slug, size, bench_seed)`; identical for all targets |
| Per-run budget | `perf.budget_ms` (default 2000): a target whose single run exceeds it is not run at larger sizes; recorded as `budget_exceeded` |
| Fresh copies | Inputs deserialized before every call, outside the timed region (in-place algorithms mutate them) |
| Order | Sizes ascending; repetitions; targets round-robin within each repetition |
| Seed | The first 8 bytes of `sha256("<slug>:<size>:<bench_seed>")` as an integer, `bench_seed` 1, so every bench of a problem sees the same inputs |
| Batching | Calls shorter than 20 ms are timed in batches: one sample makes `calls` back-to-back calls, each on its own freshly deserialized input, until it lasts at least 20 ms (at most 100000 calls, and at most `budget / elements` with a budget of 10^6 input elements in Python, whose list elements take about 36 bytes, and 10^7 in TypeScript and on the JVM; `elements` counts the input's list items, object values, string characters and other scalars, not `n`, so an input of one integer is not capped by its value). The time per call is the sample's time divided by `calls`. Without batching, sizes such as n=1e2 and often n=1e3 fall under the 50 microseconds floor below, leaving too few sizes to fit |

## Measurement

| Runtime | Time | CPU | Memory metric | Warmup | GC handling |
|---------|------|-----|---------------|--------|-------------|
| Python | `time.perf_counter_ns` | `time.process_time_ns` | `tracemalloc` peak of one separate memory call (tracemalloc slows execution); skipped at a size whose median time times 10 exceeds the budget | 1 run per size and target | `gc.collect()` before each sample |
| TypeScript (Node, started with `--expose-gc`) | `process.hrtime.bigint()` | `process.cpuUsage()` | `process.memoryUsage().heapUsed` delta of one separate memory call, from a post-`gc()` baseline to just after return | Until the coefficient of variation of the last 5 runs is at most 5%, min 3, max 20 | `gc()` before each sample |
| JVM | `System.nanoTime()` | `ThreadMXBean.getCurrentThreadCpuTime()` | `com.sun.management.ThreadMXBean.getThreadAllocatedBytes(threadId)` delta of one separate memory call: allocation volume, not peak | Same rule as Node, min 5 | `System.gc()` hint before each sample |

The first call of each target at each size is the check call ([runners](runners.md#bench-mode)); it counts as the first warmup run. Warmup also ends once it has taken `perf.budget_ms` of wall time per target and size (decoding and collection included): a call near the budget is warm after a few runs, and 20 of them would make the bench take minutes. Memory figures include the returned value. They are comparable only within one language against that language's references.

Statistics per (target, size): median of `reps` (default 7) times per call, spread = median absolute deviation / median.

## Empirical classification

### Time

1. Use sizes whose median sample lasts at least 50 microseconds (below that, timer resolution dominates; batching keeps most sizes above it). At least 3 such sizes are required, else the class is `insufficient data`.
2. Fit `log(time) = a + b * log(n)` by least squares; record slope `b` and R^2.
3. A slope `b` of 3.4 or more (above band G) is band X. Below that, classify as `exponential` only when the curve accelerates past 3.4: the local slope between the two largest sizes is at least 3.4, successive local slopes increase, and a fit of `log(time) = a + c * n` has a higher R^2 than the log-log fit. A fixed cost plus polynomial growth also has rising local slopes, but `a + b * n^k` never has a local slope above k. Over the short ladders of exponential problems (n from 4 to 40) steep polynomial and exponential growth cannot be told apart, and no declared polynomial class is steeper than `n^3`, so a fit that steep counts as exponential.
4. Map `b` to a band:

| Band | Slope `b` | Declared classes in band | Shown as |
|------|-----------|--------------------------|----------|
| A | below 0.75 | `1`, `log n`, `sqrt n` | `~1\|log n\|sqrt n` |
| C | 0.75 to 1.35 | `n`, `n log n` | `~n\|nlogn` |
| D | 1.35 to 1.75 | none (between bands) | `~n^1.5` |
| E | 1.75 to 2.35 | `n^2`, `n^2 log n` | `~n^2` |
| F | 2.35 to 2.75 | none (between bands) | `~n^2.5` |
| G | 2.75 to 3.4 | `n^3` | `~n^3` |
| X | 3.4 and above, or accelerating past 3.4 (step 3) | `2^n`, `n!` | `~2^n` |

Each band includes its lower bound and excludes its upper bound. There are no bands B and H: the sublinear classes share band A, and growth steeper than `n^3.4` is band X.

### Ladder check

`cstudy verify --ladder` compares each reference's band with the band of its declared `time_class`. A different band is a contradiction only when the declared class cannot explain the times:

| Step | Rule |
|------|------|
| Drift | For the fitted sizes and the class's growth g(n): the smallest value, over fixed costs `a >= 0`, of the largest `time / (a + g(n))` divided by the smallest. `a` stands for call overhead and lower-order terms; it may dominate the smaller sizes, but `g(n)` must be at least `a` at the three largest, which carry the growth (so a series that never grows is not explained by a fixed cost) |
| Tolerance | 4 (`DRIFT_TOLERANCE`): the factor by which the cost per unit of growth wanders across a ladder on references whose class is known (cache levels, background load, the per-seed choice of inputs) |
| Same band | `consistent` |
| Other band, drift at most 4 | `tolerated`: a warning such as `bound-search declares O(n) and measures ~1\|log n\|sqrt n (slope 0.62), but time / n varies only 1.8x, within the 4x tolerance` |
| Other band, drift above 4 | `contradicts`: a failure, such as `hash-map declares O(n) but measures ~n^2 (slope 2.00); time / n varies 160x, more than the 4x tolerance` |
| Declared `2^n` or `n!` | Band only: an exponential has no single g(n) to divide by |

### Memory

Same slope fit on the memory metric over the completed sizes that have a memory figure; values under 4 KiB count as 4 KiB, so small allocations read as constant. Bands: `constant` (below 0.3), `sublinear` (0.3 to 0.75), `linear` (0.75 to 1.35), `superlinear` (1.35 and above). At least 3 sizes are required.

## Verdict

The comparison reference is the `optimal` approach with the lowest median at the largest size both it and the user completed (the first in `meta.yaml` order on a tie).

| Condition (evaluated in order) | Verdict | Message |
|--------------------------------|---------|---------|
| User has fewer than 3 usable sizes | `unknown` | `not enough data: increase --sizes or reps` |
| No `optimal` reference completed a size the user completed | `unknown` | `no optimal reference ran in this language` |
| User exceeded the budget at a size the optimal reference completed | `suboptimal` | `exceeded budget at n=1e5 where optimal took 2.10ms` |
| The optimal reference has fewer than 3 usable sizes | `unknown` | `optimal reference hash-map has too few usable sizes` |
| User band worse than optimal band | `suboptimal` | `growth ~n^2 (slope 1.98), optimal is ~n\|nlogn` |
| Same band, ratio at largest size at most 1.5 and ratio trend below 0.1 | `optimal` | `matches hash-map, 1.12x at n=1e5` |
| Same band, ratio trend at least 0.1 | `near-optimal` | `same band but ratio grows with n: likely an extra log factor` |
| Same band, ratio above 1.5 | `near-optimal` | `same growth, 3.4x slower constant factor` |
| User band better than optimal band | `optimal` | `grows slower than hash-map`, plus content warning `beats declared optimal: check references` |

The ratio is taken at the largest size where both the user and the reference are usable. Ratio trend = slope of `log(user/optimal)` versus `log(n)` over the common usable sizes (0 with fewer than 2). A trend of 0.1 means the ratio grows about 26% per decade of `n`.

Space line: compare the user's memory band with the comparison reference's band, then name the leanest other reference measured in the same time band when it beats both: `space linear, same as hash-map; a constant-space optimal exists: two-pointers`. Other forms: `space constant, less than hash-map (linear)`, `space linear, hash-map is constant`, `space unknown: not enough memory figures`.

### Confidence

| Level | All of |
|-------|--------|
| `high` | At least 4 fitted sizes; R^2 at least 0.98 for user and reference; spread at most 10% at fitted sizes; no environment warning |
| `medium` | At least 3 fitted sizes; R^2 at least 0.95; spread at most 25% |
| `low` | Otherwise |

Fitted sizes and R^2 are the weaker of the user's and the comparison reference's (fewest sizes, lowest R^2); spread is the largest at the user's fitted sizes, as the table words it (a noisy reference shows in its own R^2). An `unknown` verdict has confidence `low`. Memory confidence uses the user's memory fit only (sizes and R^2; there is one figure per size, so no spread).

Caps: Node memory verdicts are at most `low`; JVM memory verdicts at most `medium`. Environment warnings (on battery, 1-minute load average above half the core count) cap everything at `medium`. Every verdict line prints its confidence; percentiles are never printed.

### Environment record

Each bench run stores CPU model (`sysctl -n machdep.cpu.brand_string`, else `platform.processor()`), power source (`pmset -g batt`: `AC`, `battery` or `unknown`), the 1-minute load average, the core count, the runner and runtime version from `hello`, and `references_hash`: a content hash of the reference files in that language. A content hash rather than a git hash, because references may hold uncommitted edits and the hash must change with them.

## Ranking

| Against | Shown as |
|---------|----------|
| Reference ladder | Table of every approach and the user per size, slope, band, memory band, then the verdict |
| Own history | Best previous median at the largest size this run shares with an earlier user run of the same problem and language, the change in percent, and the position among those runs (`history   best previous 13.0ms at n=1e5 (2026-09-12) · now 9% faster · 1st of 3 runs`). `--refs-only` runs are not part of the history |

## Integration

| Feature | Rule |
|---------|------|
| `cstudy test --perf` | After all cases pass: bench with `reps=3`; prints the verdict line; stored as a bench run |
| `cstudy bench` | Full report ([cli](cli.md#cstudy-bench)) |
| Storage | `bench_runs` table ([progress-and-scheduling](progress-and-scheduling.md#schema)) |
| Scheduling | With `schedule.penalize_suboptimal = true` (default), a `suboptimal` verdict of confidence `medium` or `high` for the attempt caps its grade at `hard` |
| Content gate | `cstudy verify --ladder` benches references only and fails if a reference's time band contradicts its declared `time_class` beyond the [drift tolerance](#ladder-check) (n and n log n share band C, and the sublinear classes band A, so they never contradict). A tolerated mismatch is a warning. Space is never checked against declared classes because measured memory includes outputs. A reference with fewer than 3 usable sizes (for example one that exceeds the budget early) cannot contradict its class: it is a warning that names the usable sizes and suggests smaller ladder sizes. A reference that does not load or fails on a bench input fails the gate. A problem without `generator.py` is not benched (`ladder n/a`) |
