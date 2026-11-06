# Token Cost Reconciler: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| totals-per-model | optimal | O(n log n) | O(n) | default answer |

`n` is the total number of prices, calls and report lines.

## Approach: totals-per-model (Total the tokens per model and price each total once)

### Intuition

Cost is linear in tokens, so the exact cost of a model's calls is the exact cost of its token totals. That one observation removes the most common bug: there is no per-call cost left to round. Every number stays exact until the single rounding at the very end.

The other half of the problem is about what can be wrong, and a mismatch is only useful if it says what to look at. The checks go from "which sides know this model" to "do the facts agree" to "does the money agree". A token mismatch comes before a cost mismatch because if the tokens disagree, the cost can only disagree as a consequence, and the tokens are what someone has to go and look at.

### Algorithm

1. Build a lookup of rates by model. Total the three token columns per model for the log and for the report, and total the reported costs per model.
2. Take the union of the models of the log and the report, and sort it.
3. For each model with calls and a price, compute `(input - cached) * inputRate + cached * cachedRate + output * outputRate`, divide by 1,000,000, and round to cents, half up.
4. Decide the status by the listed order, and write both amounts with two decimals, or `"-"` when that side has none.

### Correctness

Every model named by the log or the report appears once, since the rows come from the union of both, and a model only in the price table appears nowhere. Multiplication distributes over addition, so the cost of the token totals equals the sum of the exact costs of the calls, and it has no rounding error, because the constraints keep it within 28 significant digits and dividing by 1,000,000 only moves the point. The status checks follow the stated order, and each later check may assume what the earlier ones ruled out: `token-mismatch` runs only when both sides have the model, and `cost-mismatch` only when there is a computed cost.

### Complexity

- Time: O(n log n) — each input row is handled once with map lookups, and the models are sorted once.
- Space: O(n) — the maps and the rows hold at most one entry per input row.

### Trade-offs

Pricing per call instead of per total costs the same asymptotically, and it is needed once the rates change during the month, since a total can no longer be priced by one rate. Even then, you keep the exact amounts and round only the final sum.

A binary float would be shorter, and wrong by construction: it cannot hold `0.1` exactly, so its sums drift and its ties fall on the wrong side (`h4`). Money stays in a decimal type.

The tolerance exists because the two sides may round differently. It should be small. A tolerance large enough to hide a real difference stops being a check, and repeated small differences are worth noticing on their own.

### Pitfalls and edge cases

- **Billing cached tokens twice.** The input count includes the cached tokens, so the input rate applies to `input - cached`. A cached token costs a small fraction of an input token, so this bug silently inflates every computed cost (`ex1`, `h1`).
- **Rounding each call.** 100 calls at 0.0044 each round to 0.00 each, and the total disappears (`h2`). Rounding each of the three parts of a cost is the same bug in a smaller space (`h19`).
- **Half-even rounding.** Python's `round` sends `0.125` to `0.12`, and so does `Decimal.quantize` unless you name a rounding mode. The statement says half up (`h3`).
- **Floats.** `1.005` is just below itself in binary, so a float rounds it down, to 1.00 (`h4`).
- **One-directional comparison.** An under-report is a mismatch too. Comparing without the absolute value passes a report that charges less (`h5`).
- **The tolerance boundary.** A difference of exactly `tolerance` passes (`h7`, `h8`).
- **Comparing before rounding.** The computed cost is compared after its one rounding. Against the unrounded 5.556 a reported 5.56 would be a mismatch (`h9`).
- **Keeping only the last report line.** A map from model to line overwrites. A model may have several lines, and they add up (`h10`).
- **Comparing only some of the tokens.** Every column counts. A difference in cached tokens alone (`h11`), or input and output swapped with the same grand total (`h12`), is a token mismatch even when the costs agree, and it comes before a cost mismatch (`h24`).
- **Zero is an amount.** A zero token count and a zero cost are values, not absent ones, and truthiness checks confuse them (`h14`). Amounts always have two decimals (`h21`).
- **An unknown price is not a price of zero.** Costing it at 0.00 would turn the worst case, a model nobody priced, into an ordinary mismatch (`ex3`, `h17`).
- **Rows and their order.** Order is by character code, so `model-10` sorts before `model-2`, and capitals before lowercase (`h13`). A model only in the price table has no row (`h16`), and no calls and no report means no rows (`h15`).

### Language notes

- Python: `Decimal` arithmetic is exact within the default 28-digit context, an `int` times a `Decimal` is a `Decimal`, and `quantize(CENT, rounding=ROUND_HALF_UP)` is the one rounding. `f"{value:.2f}"` writes two digits, and since `computed` was already rounded it adds no rounding of its own.
- TypeScript: `Decimal` from `#support`. `movePointLeft(6)` divides by 1,000,000 exactly, `round(2, "HALF_UP")` is the rounding, and `toFixed(2)` writes two digits. `new Decimal(number)` takes a safe integer, which the constraints guarantee. `Array.prototype.sort()` with no comparator compares strings by UTF-16 code units, which for ASCII names is the stated order.
