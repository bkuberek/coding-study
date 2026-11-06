# Calibration Metrics: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| per-bin-sums | optimal | O(q (n + b)) | O(n + b) | default answer |

`n` is the number of predictions, `q` the number of rows reported and `b` the number of bins.

## Approach: per-bin-sums (Keep two running sums per bin for each group)

### Intuition

Calibration asks whether a stated probability matches how often the thing really happens. No single prediction can answer that, since a ticket either needed a human or it did not. So you pool predictions that said about the same thing, and you compare what they said with what happened. That pooling is all that a bin is, and ECE is the size-weighted average of how far each pool is from the truth.

The Brier score looks at each prediction by itself, so it rewards being sharp as well as being calibrated. A model that always predicts the base rate is perfectly calibrated and useless, and the Brier score tells the two apart where ECE does not. You want both.

Writing out one bin's contribution shows something pleasant: `(size / N) * |sum / size - trues / size|` is `|sum - trues| / N`. The bin's size cancels, so two running totals per bin are all you need, and an empty bin contributes zero with no special case.

### Algorithm

1. Group the indexes of the predictions by slice name. All predictions together form the first group.
2. For each group to report, make an array of probability sums and an array of true counts, one entry per bin.
3. For each prediction in the group, compute its bin with `min(floor(p * B), B - 1)`, add to both arrays, and add `(p - y)^2` to the squared error.
4. The ECE is the sum of `|probability sum - true count|` over the bins, divided by `N`. The Brier score is the squared error divided by `N`.
5. A group with no predictions has the row `[0, 0, 0]`.

### Correctness

The bin formula sends every probability in `[0, 1]` to exactly one index from 0 to `B - 1`, and `1.0` is capped into the last bin, so each prediction of a group is counted in one bin. By the cancellation above, the sum of `|sum - trues| / N` is the defined weighted sum: a bin with no predictions has both totals at zero and adds nothing, as defined. The slice row uses only that slice's members and its own `N`, which is what the statement asks for. Since `N` is checked first, nothing divides by zero.

### Complexity

- Time: O(q (n + b)) — grouping is one pass, and each reported group costs its size plus `b` to set up and sum the bins. Distinct slices add up to at most `n`, so the worst case needs a large slice named again and again, which a cache of rows by name would remove.
- Space: O(n + b) — the slice groups, and the arrays of one group at a time.

### Trade-offs

Equal-width bins are simple and comparable between models, but most of a confident model's predictions pile into the top bins, so the rest of the curve hardly counts. Equal-mass bins fix that and make the number harder to compare, since the edges move with the data. The bin count is itself a trade: too few bins hide errors, because a bin of mixed predictions averages them away, and too many make each bin so small that noise looks like miscalibration.

For a long report you could sort by probability and walk the bins once, but that costs `O(n log n)` and gains nothing here.

### Pitfalls and edge cases

- **Dropping the absolute value.** An overconfident bin and an underconfident one cancel, so a badly calibrated model scores 0 (`ex2`).
- **Averaging over samples instead of bins.** ECE compares the mean of a bin with its true rate. Averaging `|p - y|` over predictions is a different number, and it stays above 0 even for a perfectly calibrated group (`h12`).
- **Using the bin's midpoint as its confidence.** A bin holding `0.91` and `0.93` has a mean of 0.92, not 0.95 (`h4`).
- **Ignoring the weights.** A simple average over bins lets one stray prediction count as much as a thousand (`h5`).
- **`p = 1.0`.** `floor(p * B)` is `B`, one past the end, so the cap matters (`h1`, `h9`).
- **Bins that close on the right.** Some libraries use `(i / B, (i + 1) / B]`, which moves every probability on an edge one bin down, and drops `0.0` entirely (`h2`, `h3`). The statement fixes the convention, and comparing two tools starts with checking theirs.
- **Floating point at the edges.** `0.28 * 100` and `0.29 * 100` both land in bin 28, since `0.29 * 100` is `28.999999999999996` in a double. That is why the formula is part of the statement: code that compares against edges made by `i / B` disagrees with it there (`h10`).
- **Weighting a slice by the whole population.** A slice's `N` is its own size (`ex1`, `h6`).
- **Empty groups.** A slice with no predictions, or no predictions at all, must not divide by zero or produce `NaN` (`ex3`, `h8`).
- **An overall number can hide a broken slice.** The overall ECE can be 0 while every slice is far off (`ex3`, `h6`).
- **Sorting the rows.** Rows follow `reportSlices`, and a repeated name gets a repeated row (`h7`).

### Language notes

- Python: a `bool` is an `int`, so `true_counts[index] += outcome` and `probability - outcome` work directly. `zip(..., strict=True)` documents that the arrays are parallel.
- TypeScript: booleans need an explicit conversion to 1 or 0, since adding one to a number works only by coercion, which the type checker refuses. `new Array<number>(binCount).fill(0)` makes the bins, and without `fill` the entries are holes that turn sums into `NaN`.
