# SLO Burn Rate

## Statement

Build `SloMonitor`, the arithmetic behind a service's reliability alerts. A monitoring system reads ("scrapes") numbers from a running service every few seconds or minutes: how many requests it has served so far, how many failed, how long they took. From those readings this class works out how fast things happen, how good the service has been, how much room for failure is left, and when someone should be woken up. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**Words used throughout.** A *service level indicator* (SLI) is a measurement of how well the service is doing, written here as the share of *good* requests among all requests: "99.4% of requests succeeded" or "97% of requests finished within 300 ms". A *service level objective* (SLO) is a target for that indicator over a period: "at least 99% of requests in any 30 days are good". Since no service is perfect, the gap between the target and 100% is the *error budget*: with a 99% objective, 1% of requests may fail, and a team can "spend" that budget on risky releases or lose it to incidents. Level 3 measures the budget, and level 4 raises alerts when it burns too fast.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `SloMonitor()`: creates an empty monitor.
- All times are whole seconds, given as numbers; the class never reads a clock. A *window* `[start, end]` holds every time `t` with `start <= t <= end`, both ends included.
- A **fraction** given as an argument is a string `"p"` or `"p/q"` of whole numbers with `p >= 0` and `q >= 1`, not necessarily in lowest terms: `"99/100"`, `"990/1000"` and `"72/5"` (which is 14.4) are all valid.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods return a status string, a number, a fraction string or a list of strings, as each method states. A **fraction** that a method returns is exact: the string `"p/q"` in lowest terms with `q > 1`, or just `"p"` when the value is a whole number, with a `-` in front of a negative value. So one half is `"1/2"`, two is `"2"`, zero is `"0"`, and minus one third is `"-1/3"`. Where a value does not exist (no data, an unknown name), a method returns `""` for a string, `-1` for a number and `[]` for a list, as each method says.

## Level 1: Counters and rates

A **counter** is a number that only goes up: the requests served since the process started, the errors seen. A service exposes its counters and the monitor reads them at regular times; each reading is a *sample*, a time and a value. A counter never decreases, except in one case: when the process restarts, every counter starts again from zero. So a sample lower than the one before it means a **reset**.

The *increase* of a counter over a window is how much it went up between the first and the last sample inside the window. Going through the samples of the window in time order, each step from a value `a` to the next value `b` adds:

- `b - a` when `b >= a`;
- `b` when `b < a`: the counter was reset and counted from zero up to `b` (whatever it counted between the last sample and the restart is lost).

For example, the samples 100, 160, 250, 40, 100 increase by 60, 90, 40 and 60: 250 in total. Reading the last value minus the first, `100 - 100 = 0`, would claim nothing happened.

The *rate* over a window is the increase divided by the seconds between the first and the last sample of the window, a value per second. (Some monitoring tools also stretch the result to the edges of the window, to make up for samples that fall just inside it; this problem does not, so that every answer is exact.)

- `scrape(series, timestamp, value)`: records a sample of the counter `series`. Returns `"ok"`, or `"out-of-order"` when the series already has a sample at `timestamp` or later, in which case nothing is recorded.
- `scrapeSeries(series, start, step, values)`: scrapes `values[i]` at time `start + i * step` for each `i` in order, as `scrape` would, and returns how many of them were recorded.
- `increase(series, start, end)`: the increase over the window, computed from the samples inside it as above; `-1` when the window holds fewer than two samples of the series (an unknown series holds none).
- `rate(series, start, end)`: the rate over the window as a fraction; `""` when the window holds fewer than two samples.
- `resets(series, start, end)`: how many steps between consecutive samples inside the window go down; `0` with fewer than two samples.

### Example 1

<!-- case: ex1 -->

The counter goes 100, 160, 250, then the process restarts and it reads 40 and then 100. The increase over the whole window adds 60, 90, 40 and 60, which is 250 requests in 240 seconds: a rate of 25/24 per second, with one reset. Between 60 and 120 the counter went from 160 to 250. The window from 100 to 110 holds no sample, so there is no increase and no rate. A second sample at 240 is refused.

### Example 2

<!-- case: ex2 -->

Six samples, 30 seconds apart. The window from 0 to 150 adds 2, 0, 3, then 1 after a reset, then 2: an increase of 8 and a rate of 8/150, written 4/75. The window from 31 starts at the sample taken at 60. Scraping again from 120 records only the value for 180, since the series already has samples at 120 and 150.

## Level 2: Latency histograms

How long requests take cannot be kept as one counter per request, so services keep a **histogram**: a few *buckets*, each with an upper bound in milliseconds, and for each bucket a counter of the requests that took *at most* that long. The buckets are *cumulative*: a request of 80 ms counts in the bucket for 100 ms and in every larger one. A last bucket with no upper bound (written `inf`) counts every request, so it is the total.

So a histogram is just a group of counters. When the monitor scrapes a histogram named `latency` with the bounds `[100, 250]`, it records one counter per bucket, named `latency:le=100`, `latency:le=250` and `latency:le=inf` (`le` reads "less than or equal"). Every method of level 1 works on them, and the increase of each bucket over a window gives the histogram of the requests of that window. The buckets of a histogram restart together.

**The share of fast requests.** With the window's bucket increases, the share of requests that took at most `B` milliseconds is the bucket for `B` divided by the `inf` bucket, *when `B` is one of the bounds*. For any other threshold the histogram cannot say how many requests in a bucket were below it, so the answer does not exist. This is why a latency SLI uses a threshold that is a bucket bound.

**Quantiles.** The `q`-quantile of the latencies (for example the 0.99-quantile, "99% of requests were at least this fast") is estimated from the buckets by assuming that the requests inside a bucket are spread evenly between its lower and upper bound. With `n` requests in the window:

1. The *rank* is `q * n`, the number of requests at or below the quantile.
2. Find the first bucket, in order of the bounds, whose count is at least the rank.
3. If that is the `inf` bucket, the answer is the largest bound: nothing more precise can be said.
4. Otherwise the bucket runs from `lower` to `upper`: its own bound is `upper`, and `lower` is the bound of the bucket before it, or `0` for the first bucket. With `below` the count of the bucket before it (`0` for the first) and `count` its own count, the answer is `lower + (upper - lower) * (rank - below) / (count - below)`.

For example, with 100 requests of which 40 took at most 100 ms and 70 at most 250 ms, the 0.5-quantile has rank 50; the first bucket that reaches 50 is the one for 250 ms, which holds 30 requests between 100 and 250 ms, so the estimate is `100 + 150 * (50 - 40) / 30 = 150` ms.

- `scrapeHistogram(name, timestamp, bounds, counts)`: records a histogram sample: `bounds` are the upper bounds of the buckets in increasing order, and `counts` has one more entry than `bounds`, the cumulative counts of each bucket and then the total. Each count is scraped into the counter of its bucket as described. Returns `"ok"`, or `"out-of-order"` when the histogram already has a sample at `timestamp` or later, in which case nothing is recorded.
- `fractionWithin(name, threshold, start, end)`: the share of the window's requests that took at most `threshold` ms, as a fraction. `""` when the histogram is unknown, `threshold` is not one of its bounds, or the window has no requests (the `inf` bucket's increase is `-1` or `0`).
- `quantile(name, q, start, end)`: the `q`-quantile of the window's requests, estimated as above, as a fraction of milliseconds. `q` is a fraction with `0 < q <= 1`. `""` when the histogram is unknown or the window has no requests.

### Example 1

<!-- case: ex3 -->

In the first minute 100 requests came in: 40 within 100 ms, 70 within 250 ms, 90 within 500 ms and 98 within 1000 ms. So 7/10 took at most 250 ms, while a threshold of 300 ms is not a bound and has no answer. The median is 150 ms, as worked out above. The 0.9-quantile has rank 90, reached exactly at the end of the 500 ms bucket. The 0.99-quantile has rank 99, which only the `inf` bucket reaches, so the answer is the largest bound, 1000. Each bucket is a counter of its own.

### Example 2

<!-- case: ex4 -->

The service restarts between the second and the third sample, and every bucket drops. Each bucket's increase counts the steps before and after the restart: 25 requests within 200 ms out of 42. The median has rank 21 and falls in the first bucket, which starts at 0: `200 * 21 / 25 = 168`. The 0.75-quantile has rank 63/2 and falls in the second bucket, between 200 and 400 ms, at 860/3 ms. A second sample at the same time is refused.

## Level 3: Error budgets

An **SLO** names a counter of good requests, a counter of all requests, an *objective* `o` (a fraction between 0 and 1) and a *window* `W` in seconds: "the share of good requests over the last `W` seconds should be at least `o`". The window *rolls*: at any time `at` it covers `[at - W, at]`, so old requests leave it as new ones come in. For a latency objective, the good counter can be a histogram bucket such as `latency:le=300` and the total its `inf` bucket.

Over the window, let `total` be the increase of the total counter, `good` that of the good counter, and `bad = total - good`. Then:

- the **SLI** is `good / total`;
- the **error budget** is the share of requests allowed to be bad, `e = 1 - o`: with an objective of 99/100 it is 1/100, so 1 bad request in 100 is within the objective;
- the **budget remaining** is the part of the budget not spent yet, `1 - (bad / total) / e`: `1` when nothing failed, `0` when exactly the allowed share failed, and below `0` when the objective is missed.

**Burn rate.** The *burn rate* over a recent *lookback* period says how fast the service spends its budget, relative to the objective: the share of bad requests over `[at - lookback, at]`, divided by `e`. A burn rate of 1 spends exactly the whole budget over one SLO window; a burn rate of 2 spends it in half the window, 10 in a tenth of it. So with a 30-day window, a burn rate of 10 empties a full budget in 3 days.

**Time to exhaustion.** If the burn rate of the lookback goes on, the budget that is left runs out after `remaining * W / burn` seconds. In terms of the counts, with `o = om / od` as given (so `e = (od - om) / od`), the window's `total` and `bad`, and the lookback's `t` and `b`, this is

`W * (total * (od - om) - bad * od) * t / (total * b * od)`

rounded down to a whole number of seconds. The tests keep every product in this formula below 2^63, but some go above 2^53, the largest whole number a JavaScript `number` holds exactly.

- `defineSlo(name, goodSeries, totalSeries, objective, window)`: defines an SLO. The series do not need to exist yet. Statuses, in this order: `"duplicate"` when an SLO with this name exists; `"bad-objective"` when the objective is not strictly between 0 and 1; otherwise `"ok"`.
- `sli(name, at)`: the SLI over `[at - W, at]` as a fraction. `""` when the SLO is unknown, the total counter's increase is `-1` or `0`, or the good counter's increase is `-1`.
- `budgetRemaining(name, at)`: the budget remaining over `[at - W, at]` as a fraction, possibly negative; `""` exactly when `sli` is `""`.
- `burnRate(name, at, lookback)`: the burn rate over `[at - lookback, at]` as a fraction; `""` when the SLO is unknown or that window has no requests in the sense of `sli`.
- `timeToExhaustion(name, at, lookback)`: checked in this order: `-1` when `budgetRemaining(name, at)` is `""`; `0` when the budget remaining is `0` or less; `-1` when the burn rate over the lookback is `""` or `0` (the budget is not shrinking); otherwise the formula above.

### Example 1

<!-- case: ex5 -->

Over four hours the service served 4,000 requests and 38 failed: 4, 4, 10 and then 20 in the last hour. The SLI is 3962/4000, written 1981/2000. With a 99% objective, 40 failures were allowed, so 38/40 of the budget is spent and 1/20 remains. The last hour failed 2% of its requests, twice the 1% budget: a burn rate of 2. Over the last two hours it is 30 in 2,000, a burn rate of 3/2. At a burn rate of 2, a full 30-day budget would last 15 days; 1/20 of it lasts 18 hours, 64,800 seconds. Two hours in, the window held 8 failures in 2,000 requests.

### Example 2

<!-- case: ex6 -->

An SLO name can be used once, and an objective of 1 (100%) leaves no budget at all, so it is refused, like 0. Before any sample there is no SLI. With a 99.9% objective, 1 failure in 1,000 requests is allowed, and 3 failed, so the budget remaining is `1 - 3 = -2`: twice the budget is overspent, and the time to exhaustion is 0. The last minute burns at 6. A minute earlier nothing had failed, so the budget was not shrinking and the time to exhaustion was `-1`.

## Level 4: Multi-window burn-rate alerts

An alert should wake someone up when the error budget is in real danger, and only then. That is harder than it looks:

- **One threshold on a short window pages too often.** Alerting whenever the last five minutes miss the objective fires on every small blip, most of which use a tiny part of the budget, and pages that rarely matter teach people to ignore pages.
- **One threshold on a long window pages too late and stops too late.** Averaged over a long window, a sudden outage takes a while to push the error share over the threshold, and once the outage is over, the bad minutes stay inside the window and keep the alert firing long after the service has recovered. The time an alert keeps firing after the problem is fixed is its *reset time*.

**Burn-rate alerts** compare the burn rate, not the error share, with a threshold, and a threshold has a meaning in budget: a burn rate `B` held for a period `p` spends `B * p / W` of the budget. Over a 30-day window (720 hours), a burn rate of 14.4 for one hour spends `14.4 * 1 / 720 = 2%` of the budget; a burn rate of 6 for six hours spends 5%; a burn rate of 1 for three days spends 10%. A common starting point is to page for the first two and open a ticket for the third.

**Two windows per alert.** Each alert has a *long* window that measures the burn rate (has enough budget been spent to matter?) and a *short* window, often a twelfth of the long one, that checks the burn is still happening. The alert fires only while **both** burn rates are **strictly above** the threshold. The long window keeps it from firing on blips; the short window makes it stop within minutes of recovery. Several such alerts with different windows and thresholds, one per severity, catch fast and slow burns alike.

- `addAlert(slo, severity, longWindow, shortWindow, threshold)`: adds an alert to the SLO. `threshold` is a fraction above 0. A `shortWindow` of `0` means the alert has only the long window. Statuses, in this order: `"unknown-slo"`; `"duplicate"` when the SLO already has an alert with this severity; `"bad-windows"` when `longWindow <= 0`, `shortWindow < 0` or `shortWindow >= longWindow`; otherwise `"ok"`.
- `firing(slo, at)`: the severities of the SLO's alerts that fire at time `at`, in the order the alerts were added. An alert fires when the burn rate over `[at - longWindow, at]` is above the threshold and, unless `shortWindow` is `0`, so is the burn rate over `[at - shortWindow, at]`. A window whose burn rate is `""` (no requests) is not above anything. `[]` for an unknown SLO.
- `timeline(slo, start, end, step)`: evaluates every alert of the SLO at the times `start`, `start + step`, `start + 2 * step` and so on, up to and including `end` when it is reached. Before `start` no alert is firing. Each time an alert changes from not firing to firing, the list gets `"<time> <severity> start"`, and each time it changes back, `"<time> <severity> stop"`. Events are in time order, and the events of one time in the order the alerts were added. `[]` for an unknown SLO, or when `start > end`.

### Example 1

<!-- case: ex7 -->

The service gets 100 requests every 5 minutes against a 99% objective. From 3,600 to 5,400 seconds half of them fail, and in the 5 minutes before 9,000 there is a blip of 20 failures. Three alerts share the threshold 14.4 (written 72/5). `short-only`, with a 5-minute window alone, starts at 3,900 as soon as one bad interval is seen, and pages again for the blip, which spent only a small part of the budget. `long-only`, with a one-hour window alone, waits until 4,800, when 200 of the last hour's 1,200 requests have failed, and then keeps firing until 8,100, 45 minutes after the outage ended. `page` needs both: it starts at 4,800 with the long window and stops at 5,700, five minutes after recovery.

### Example 2

<!-- case: ex8 -->

Steady trouble: 8% of requests fail for two hours, a burn rate of 8. The fast page (one hour and 5 minutes at 14.4) never fires, but the slow page (six hours and 30 minutes at 6) and the ticket (three days and six hours at 1) both do: a burn rate of 8 held for days would empty the budget long before the month is over. With only two hours of samples, the long windows hold what there is. A second `ticket` is a duplicate, a short window as long as the long one is refused, and an alert needs an SLO. At time 0 no window holds two samples yet, so nothing fires; checked every 30 minutes, both alerts start at 1,800.

## Constraints

- Times are between 0 and 10^9; a window may reach below 0 (`at - W` can be negative). Windows, lookbacks and alert windows are at most 30 days, 2,592,000 seconds.
- Series, histogram, SLO and severity names are 1 to 40 characters of small letters, digits, `_` and `-`; only the counters of a histogram's buckets carry the `:le=` part.
- Counter values are between 0 and 10^9, and the increase of any counter over any window that a method reads is at most 10^4.
- When a process restarts, its counters start again from zero. In the tests every restart shows: at the first sample after it, each counter that had counted anything reads lower than at the sample before, and the buckets of a histogram restart together. A histogram's bounds are 1 to 20 positive increasing numbers, at most 10^6, the same at every scrape, and its counts never decrease from one bucket to the next.
- In every fraction argument, `q <= 1000`, and `p <= 10^4`.
- At most 10^4 samples per series, at most 10^4 calls per test, and at most 10^4 times evaluated by one `timeline`.

## Follow-ups

- This problem computes rates from the samples inside a window only. What changes when the first and last samples sit well inside the window, and how would you stretch the increase to the window's edges? What can go wrong near a reset?
- A low-traffic service with 10 requests an hour has a 10% error share after one failure. How would you keep such a service from paging on every single failure, without missing a real outage?
- A histogram's buckets are fixed in advance. What happens to the quantile estimate when the objective's threshold falls between two bounds, or when most requests land in one wide bucket?
- `timeline` recomputes every window at every step. How would you keep running sums so that each step costs O(1) per alert?
- The time to exhaustion assumes the burn rate of the lookback goes on. How would requests leaving the rolling window change the answer?

## Hints

### Hint 1

Keep the samples of each series in a list, in time order; `scrape` only ever appends. A window is then a slice of that list, and every method of level 1 is a loop over the slice.

### Hint 2

Write one function that turns two whole numbers into the fraction string: divide both by their greatest common divisor, and drop the denominator when it is 1. Every ratio of the problem, rates, shares, SLIs, burn rates, goes through it, so the format is right everywhere at once.

### Hint 3

To find the window's slice quickly, search the sorted list of times for the first time at or after `start` and the last time at or before `end`. Binary search finds both.

### Hint 4

A histogram adds nothing new: store each bucket as an ordinary counter under the name the statement gives, and compute each bucket's increase with level 1's method. Then the quantile is a walk over a short list of numbers. Compare the counts with the rank by multiplying instead of dividing, so nothing needs to leave whole numbers until the very end.

### Hint 5

Write one helper that returns the bad and total requests of an SLO over `[at - span, at]`, or nothing when there are no requests. The SLI, the budget, the burn rate and the alert windows all call it with different spans.

### Hint 6

A burn rate is above a threshold `p/q` when `bad * od * q > p * total * (od - om)`, with the objective `om / od`. Comparing the two products avoids building fractions in the alert loop.

### Hint 7

For `timeline`, keep one flag per alert, all false before the first step. At each time, evaluate the alerts in the order they were added and emit an event only when an alert's state differs from its flag, then update the flag.
