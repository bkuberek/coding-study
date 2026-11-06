# Calibration Metrics

## Statement

A classifier scores support tickets with the probability that a ticket needs a human. Someone will pick a threshold on that score, so the score has to mean what it says: of the tickets scored around 0.8, about 80% should really need a human. Accuracy cannot tell you this, because a model can rank tickets perfectly and still be overconfident.

The predictions are already recorded, so no model runs here. Write `calibrationReport`, which measures how well they are calibrated, overall and per slice.

For a **group** of `N` predictions, with `binCount` written as `B`:

- **Bins.** Each prediction goes to the bin `min(floor(p * B), B - 1)`, computed in double precision exactly like this. Bin `i` therefore holds probabilities from `i / B` up to but not including `(i + 1) / B`, except that the last bin also holds `1.0`.
- **Expected calibration error (ECE).** For each bin with at least one prediction, take the mean probability of its predictions and the fraction of them whose outcome is true. The bin contributes `(its size / N) * |mean probability - fraction true|`. The ECE is the sum over the bins, and an empty bin contributes nothing.
- **Brier score.** The mean over the group of `(p - y)^2`, where `y` is 1 when the outcome is true and 0 otherwise.

The report has one row per group, `[N, ECE, Brier]`. The first row is the group of all predictions, and then there is one row per entry of `reportSlices`, in that order, for the predictions whose slice has that name. Each slice is binned and weighted by itself: its `N` is its own size. A group with no predictions has the row `[0, 0, 0]`.

## Input

- `probabilities`: the recorded probability of each prediction.
- `outcomes`: `outcomes[i]` is what really happened for prediction `i`.
- `sliceNames`: `sliceNames[i]` is the slice prediction `i` belongs to, such as the channel it came from. Names are compared exactly.
- `reportSlices`: the slices to report on. A name may repeat, and it may name a slice with no predictions.
- `binCount`: the number of equal-width bins.

## Output

A list of `1 + reportSlices.length` rows, each `[N, ECE, Brier]`. Numbers are compared with a tolerance of `1e-9`, relative to the size of the expected number when it is above 1.

## Examples

### Example 1

<!-- case: ex1 -->

With two bins, overall, `0.1` and `0.4` fall in the low bin: mean probability 0.25, nothing true, so it contributes `(2 / 4) * 0.25 = 0.125`. `0.7` and `0.9` fall in the high bin: mean probability 0.8, all true, so it contributes `(2 / 4) * 0.2 = 0.1`. The ECE is 0.225, and the Brier score is `(0.01 + 0.16 + 0.09 + 0.01) / 4 = 0.0675`. `mobile` is the group `0.1, 0.7`, binned and weighted by itself: `(1 / 2) * 0.1 + (1 / 2) * 0.3 = 0.2`.

### Example 2

<!-- case: ex2 -->

The low bin is too low by 0.8 and the high bin is too high by 0.8. Without the absolute value they would cancel to 0. Here there are no slices to report, so the result has only the row for all predictions.

### Example 3

<!-- case: ex3 -->

Every prediction is 0.5 and half of them come true, so overall the model looks perfect: an ECE of 0. Each slice tells the truth: `mobile` is always true and `web` never is, each off by 0.5. This is why you look at slices at all. `tablet` has no predictions, so its row is all zeros.

## Constraints

- `0 <= probabilities.length == outcomes.length == sliceNames.length <= 10^5`.
- `0 <= probabilities[i] <= 1`.
- `1 <= binCount <= 1000`.
- `0 <= reportSlices.length <= 100`, and every name is 1 to 40 characters long.

## Follow-ups

- Report the maximum calibration error: the worst bin instead of the weighted sum.
- Use equal-mass bins, each holding about the same number of predictions. What breaks when many predictions share one probability?
- A slice of ten predictions can show a large ECE by chance alone. How would you tell when a slice is too small to trust, and what would you put in the report?

## Hints

### Hint 1

Write the contribution of one bin out as a fraction, and see what cancels.

### Hint 2

A slice is just another group. One helper that takes a list of predictions can produce every row.

### Hint 3

Check what your bin index does with `p = 1.0`.
