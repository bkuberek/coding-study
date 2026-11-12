# SLO Burn Rate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| exact-window-increases | optimal | O(log S + k) per window over S samples with k inside it; O(B (log S + k)) per histogram query of B buckets; O(N A (log S + k)) per timeline of N instants and A alerts | O(S) for all the samples | default answer; one window increase serves counters, histograms, SLOs and alerts |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Samples per series; the increase over a window with resets counted from zero | for each series, the sample times and values in two parallel lists |
| 2 | A histogram is one counter per bucket, under a derived name | the bounds of each histogram; its buckets live with the other counters |
| 3 | SLOs as ratios of two window increases, kept as integers | each SLO's two series, its objective as given (`om / od`) and its window |
| 4 | Alerts compare burn rates with thresholds by cross-multiplying | each SLO's alerts in the order they were added |

The early choice that keeps the later levels small is to store bucket counts as ordinary counters. Level 2 then needs no reset logic of its own, and level 3 can name a bucket as the good counter of a latency objective. The second choice is never to leave whole numbers: every ratio is kept as a numerator and a denominator and reduced only when it is printed, so every answer is exact in every language.

## Approach: exact-window-increases (Reset-aware window increases and exact fractions)

### Intuition

Everything in the problem is the increase of a counter over a window. A rate divides it by the time between samples, a histogram is the increase of each bucket, an SLI is one increase over another, a burn rate is an SLI turned around and divided by the budget, and an alert compares two burn rates with a threshold. So one careful function, the increase with resets, carries the whole problem; the rest is arithmetic on its results, done with integers so that the answers are exact.

### Algorithm

1. Level 1: `scrape` appends to the series' lists after checking that the time is later than the last one. For a window, two binary searches find the first sample at or after `start` and the last at or before `end`. The increase walks consecutive pairs of that slice and adds `b - a`, or `b` after a drop; `resets` counts the drops; `rate` divides the increase by the time between the first and last samples of the slice and reduces the fraction by the greatest common divisor.
2. Level 2: `scrapeHistogram` checks the time against the `inf` bucket and scrapes each count into `name:le=<bound>` and `name:le=inf`. A query computes every bucket's increase over the window and gives up when the `inf` bucket's is not positive. `fractionWithin` divides the bucket of the threshold by the total. `quantile` keeps `q = top / bottom` and finds the first bucket with `count * bottom >= top * total`; for a finite bucket it returns `(lower * bottom * inside + (upper - lower) * (top * total - bottom * below)) / (bottom * inside)`, which is the interpolation formula with every term over one denominator.
3. Level 3: a helper returns `(bad, total)` over `[at - span, at]`, or nothing without requests. With the objective `om / od` and `spare = od - om`, the budget remaining is `(total * spare - bad * od) / (total * spare)`, the burn rate is `(bad * od) / (total * spare)`, and the time to exhaustion is `W * (total * spare - bad * od) * t / (total * b * od)` with integer division, after the special cases.
4. Level 4: an alert fires when, for its long window and (unless it is 0) its short window, `bad * od * thresholdBottom > thresholdTop * total * spare`. `timeline` walks the times from `start` by `step`, keeps one flag per alert, and emits an event whenever an alert's state differs from its flag.

### Correctness

Increase: between two consecutive samples `a` and `b` of the same process, the counter only grew, so it counted `b - a`. If the process restarted in between, the counter started again from 0 and is now at `b`, so it counted `b` since the restart; what it counted before the restart and after the sample `a` is unknown and lost. The statement guarantees that a restart always shows as a drop, so `b < a` exactly when there was a restart, and the sum over all steps is the number of events between the first and last samples, minus only what restarts lost.

Histogram: each bucket counter is a counter in its own right, so its window increase is the number of requests of the window that took at most its bound. Because the buckets restart together and every restart shows as a drop in every bucket that counted anything, the increases are cumulative too: each is at least the one before. So the first bucket whose count reaches the rank exists (the `inf` bucket's count is the total, and the rank is at most the total), and the bucket before it holds fewer requests than the rank, so `count - below > 0` and the interpolation is defined.

Budget and burn rate: with `e = spare / od`, the budget remaining `1 - (bad / total) / e` equals `(total * spare - bad * od) / (total * spare)` after multiplying through by `total * spare`, which is positive. The burn rate `(b / t) / e` equals `(b * od) / (t * spare)` the same way. The time `remaining * W / burn` becomes `W * (total * spare - bad * od) * t / (total * b * od)`; the factor `spare` cancels. Integer division of two positive numbers rounds down, as the statement asks.

Alerts: `burn > p / q` with positive denominators is equivalent to `bad * od * q > p * t * spare`, so the comparison is exact. `timeline` reports a change exactly when the state at a time differs from the state at the previous time, and before the first time every flag is false, as the statement says.

### Complexity

- Time: O(log S + k) per window over S samples with k inside it; O(B (log S + k)) per histogram query of B buckets; O(N A (log S + k)) per timeline of N instants and A alerts — each window costs two binary searches and a walk over its samples; a histogram query does that once per bucket; a timeline evaluates two windows per alert at each of its times.
- Space: O(S) for all the samples — every sample is stored once; histograms, SLOs and alerts add a few numbers each.

### Trade-offs

- Walking the window's samples is simple and exact. A long timeline over long windows repeats most of that work at every step; prefix sums of the per-step increases (with resets already applied) would make each window O(log S), at the price of keeping them up to date as samples arrive.
- Keeping samples forever is what makes any window answerable. A real system keeps a limited history and precomputes the window ratios it alerts on, so an alert reads a few stored numbers instead of raw samples.
- Exact fractions make every language agree. Floating-point ratios are what monitoring systems use, and they are fine for dashboards; for a test that compares answers across six languages, and for thresholds compared at equality, exactness is the safer choice.
- The time to exhaustion assumes the lookback's burn rate goes on and ignores requests that will leave the rolling window. It is an estimate for prioritising work, not a forecast.

### Pitfalls and edge cases

- A reset adds the new value, not the difference: last value minus first value is wrong across a restart, and a negative step would subtract real traffic. A counter that stays the same is not a reset.
- The rate divides by the time between the first and last samples of the window, not by the length of the window asked for. Both ends of the window are included; a sample exactly at `start` belongs to it, and so does one exactly at `end`.
- `scrapeSeries` returns how many samples were recorded, not how many were given.
- The quantile takes the first bucket whose count is *at least* the rank, the first bucket starts at 0, the bucket before an empty bucket gives its lower bound, and a quantile beyond the last finite bound answers that bound.
- `fractionWithin` has no answer between bounds; interpolating there would invent a precision the histogram does not have.
- The error budget is `1 - objective`. Dividing the bad share by the objective instead gives burn rates near the bad share itself, which never reach any useful threshold.
- An overspent budget gives a negative remaining budget and a time to exhaustion of 0; a lookback without failures gives `-1`; a time that is not a whole number of seconds rounds down.
- An alert fires only when both windows are strictly above the threshold. A window without two samples, or without requests, is not above anything, so a short window shorter than the scrape interval never fires.
- Events of the same time follow the order in which the alerts were added, not their names, and the last time `end` is evaluated when `step` reaches it.
- Integer overflow: the time to exhaustion multiplies four numbers. They stay below 2^63, so 64-bit integers are enough, but a 32-bit `int` overflows, and so does exactness in a JavaScript `number` past 2^53.

### Language notes

- Python's integers never overflow and `math.gcd` reduces fractions; `bisect_left` and `bisect_right` find the window. `fractions.Fraction` would also work, at some cost in speed.
- TypeScript computes everything with `number`, which is exact for whole numbers up to 2^53, except the time to exhaustion, which uses `BigInt` for its products and converts the quotient back to a `number`.
- Java and Kotlin use `long` throughout and reduce with a small recursive `gcd`. Java writes the binary search over the `Long` times by hand; Kotlin calls `binarySearch` with a comparison that never answers 0, so the result always encodes the insertion point.
- Go uses `int64` for times, values and products and `sort.Search` for the window; Rust uses `i64` and `partition_point` on a `Vec<i64>`.
- All six compare the burn rate with a threshold by cross-multiplying whole numbers; those products stay far below 2^53, so even a JavaScript `number` is exact there.

## Further reading

- *The Site Reliability Workbook*, ["Alerting on SLOs"](https://sre.google/workbook/alerting-on-slos/): the definition of burn rate, the table of burn rates and times to exhaust a 30-day budget, the precision, recall, detection time and reset time of an alert, and the multiwindow, multi-burn-rate alerts with their recommended windows (1 hour and 5 minutes at 14.4, 6 hours and 30 minutes at 6, 3 days and 6 hours at 1) and the short window of a twelfth of the long one.
- *The Site Reliability Workbook*, ["Implementing SLOs"](https://sre.google/workbook/implementing-slos/): the SLI as the ratio of good events to all events, the error budget as 100% minus the SLO, and rolling against calendar windows.
- *Site Reliability Engineering*, ["Service Level Objectives"](https://sre.google/sre-book/service-level-objectives/): what SLIs and SLOs are, and why latency is better read as percentiles than as an average.
- Prometheus documentation, ["Metric types"](https://prometheus.io/docs/concepts/metric_types/): counters that only increase or reset to zero on restart, and histograms as cumulative bucket counters labelled with their inclusive upper bound, the `+Inf` bucket being the total count.
- Prometheus documentation, ["Query functions"](https://prometheus.io/docs/prometheus/latest/querying/functions/): `rate()`, `increase()` and `resets()`, which adjust for counter resets and, unlike this problem, extrapolate to the ends of the range, and `histogram_quantile()`, which interpolates linearly within a bucket, takes 0 as the lower limit of the lowest bucket, and returns the second highest bucket's upper bound for a quantile in the `+Inf` bucket.
