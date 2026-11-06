# Token Cost Reconciler

## Statement

A platform team sends every model call through one gateway, which logs the tokens of each call. At the end of the month a billing report arrives with what the team is being charged. Before anyone pays it, your code compares the two and flags every model where they disagree.

All names and prices here are invented. A model has three rates, each a price per 1,000,000 tokens:

- the **input** rate, for input tokens that were not served from a cache,
- the **cached-input** rate, for input tokens that were,
- the **output** rate.

The **input tokens of a call include its cached tokens**. A call with 1,000 input tokens of which 300 were cached pays the input rate on 700 and the cached-input rate on 300.

**Computed cost.** Add up the exact cost of all of a model's calls, and round that total once to cents, half up (a tie such as `0.125` goes to `0.13`). Nothing is rounded before the total.

**Reported values.** A model may have several lines in the report. Add up its tokens and its costs.

Write `reconcileUsage`, which returns one row per model named in the log or in the report, sorted by model name in ascending order of character codes. The status of a model is the first of these that applies:

1. `unpriced-model`: the model has calls, but no price.
2. `not-in-log`: the report has the model, but the log has no calls of it.
3. `missing-from-report`: the log has calls of the model, but the report has no line for it.
4. `token-mismatch`: any of the three token totals (input, cached, output) differs between the log and the report.
5. `cost-mismatch`: the computed cost and the reported cost differ by more than `tolerance`, in either direction. A difference of exactly `tolerance` is fine.
6. `ok`: none of the above.

## Input

- `priceModels`, `prices`: `prices[i]` is `[input, cachedInput, output]`, the rates of `priceModels[i]`.
- `callModels`, `callTokens`: one entry per logged call. `callTokens[i]` is `[inputTokens, cachedTokens, outputTokens]` for a call of `callModels[i]`.
- `reportedModels`, `reportedTokens`, `reportedCosts`: one entry per line of the report. `reportedTokens[i]` has the same three columns, and `reportedCosts[i]` is the amount charged on that line.
- `tolerance`: the largest difference in cost to let pass.

Decimals are exact base-10 numbers.

## Output

The rows of the report, each `[model, status, computedCost, reportedCost]`. An amount is written with exactly two digits after the point, such as `"5.60"`, and it is `"-"` when that side has no amount: the computed cost of a model without calls or without a price, and the reported cost of a model without a line in the report.

## Examples

### Example 1

<!-- case: ex1 -->

The call has 1,000,000 input tokens, of which 400,000 were cached. So 600,000 tokens at 4.40 cost 2.64, 400,000 tokens at 0.44 cost 0.176, and 200,000 output tokens at 13.70 cost 2.74. The total of 5.556 rounds to 5.56, which is what was reported.

### Example 2

<!-- case: ex2 -->

`model-a`'s tokens add up across its two calls and agree with the report, but its cost is 0.1428, which rounds to 0.14, and 0.25 was reported. `model-b`'s output tokens differ. Its costs differ too, but a token difference comes first in the list.

### Example 3

<!-- case: ex3 -->

`model-a` has calls but no line in the report. `model-c` has no price, so nothing can be computed for it. `model-d` is charged for without a single logged call.

## Constraints

- `0 <= priceModels.length <= 100`, and the names in it are distinct.
- `0 <= prices[i][j] <= 1000`, with at most 4 fractional digits.
- `0 <= callModels.length, reportedModels.length <= 10^4`.
- `0 <= cachedTokens <= inputTokens`, and `0 <= outputTokens`, in the log and in the report.
- Any token total of one model stays below `10^15`.
- `0 <= reportedCosts[i] <= 10^9` and `0 <= tolerance <= 100`, each with at most 2 fractional digits.
- Model names are 1 to 40 ASCII characters long, and they are compared exactly.
- These bounds keep every exact amount within 28 significant digits.

## Follow-ups

- Prices change. Give each rate a date from which it applies, and price each call by its own day (see `versioned-rate-table`).
- Report by day, not by month, so that a mismatch points at the day it began.
- Tokens agree but the costs do not: what does that say about whose price table is out of date, and how would you show the implied rate?

## Hints

### Hint 1

Cost is linear in tokens. Adding up a model's tokens and pricing the totals gives the same exact number as pricing each call and adding those.

### Hint 2

Rounding is the last thing that happens, and it happens once per model.

### Hint 3

Work out the six statuses as questions about which of the three sides, log, report and price table, know the model.
