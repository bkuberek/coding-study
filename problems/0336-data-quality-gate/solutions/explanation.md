# Data Quality Gate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rules-as-data | optimal | O(r c + r log b) per validate or decide, r rows, c rule columns, b drift bins | O(r + d) for r rows and d dimension keys | default answer; one rule record and one dispatch on the check name serve all four levels |

Here `r` is the number of rows in a batch, `c` the total number of columns over all rules, `b` the number of drift bins and `d` the number of dimension keys.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Rules as records and one check per value | a list of rules in the order added, a map from rule id to rule, and the column positions |
| 2 | Checks that read several rows or the previous batch | the dimension key sets and the previous batch |
| 3 | Drift and freshness | the clock; drift reads the previous batch kept at level 2 |
| 4 | Actions and the decision | an action on each rule and the rows set aside by the last decision |

The early choice that keeps level 4 small is a single function that returns, for one rule, its findings over a given list of rows, plus a single function that returns the rows a row rule fails. `validate` calls the first over all rules; `failingRows` calls the second. The gate is then two loops over the same functions, the row rules on all rows and the batch rules on the rows left, and nothing about the checks has to change.

## Approach: rules-as-data (Rules kept as data and checked one pass each)

### Intuition

Every check answers one of two questions: which rows fail, or does the batch as a whole fail. The first kind can quarantine, because there is something to set aside; the second can only warn or block. Keeping each rule as data (check name, columns, parameters, action) makes the order of the report the order of a list, makes the dispatch one switch on the check name, and lets the gate reuse the checks unchanged. The subtle parts are not the loops but the edges of each check: what counts as null, what counts as an integer or a date, how bounds round, which bin an edge belongs to, and which rows a batch rule sees.

### Algorithm

1. `addRule` refuses a used id, an unknown check, an unknown column, and a reference to a dimension that is not loaded; otherwise it appends the rule with the action `block`.
2. A value check tests null first: `not-null` fails exactly the empty string, and every other check passes it. `type` parses by hand (an optional minus and 1 to 15 digits; four digits, dash, two, dash, two, and a day within the month's length); `allowed` is set membership; `range` applies only to valid integers; `references` looks the value up in the dimension's set as it is now.
3. `unique` maps each complete key, as a tuple of column values, to its rows, and fails every row of a group of two or more.
4. `row-count` computes `floor(P (100 - t) / 100)` and `ceil(P (100 + t) / 100)` in integers and compares.
5. `drift` counts the integer values of each batch per bin, with a binary search over the edges, turns counts into shares, replaces zero shares with `0.0001`, sums `(a - e) ln(a / e)`, and rounds to an integer number of ten-thousandths. It fails when that number is at least the threshold read in the same units.
6. `freshness` takes the largest integer in the column; no integer fails with `none`, otherwise the lag is compared with the limit.
7. `decide` collects the rows failed by quarantine rules, runs the batch rules on the rows left, orders the findings by rule, and blocks when any finding's action is `block`. Only a publish updates the previous batch and the quarantined rows.

### Correctness

Each finding is computed by the definition of its check over the rows it is given, so `validate` returns exactly the failing rule and column pairs, in the order of the rule list and then the rule's column list.

The gate's two passes match the statement's order: the rows set aside are the union of the rows failed by quarantine rules, all computed on the full batch, so the result does not depend on the order of the rules; the batch rules then see exactly the rows that would be published. The decision is `block` exactly when some failing rule blocks, and the state changes (previous batch, quarantined rows) happen only after the decision is known to be `publish`, so a blocked batch leaves the gate as it was.

Rounding is computed once, in integer units, so the text and the comparison with the threshold always agree. The cases keep every PSI at least a millionth of a unit away from a half, so a difference in the last bit of a logarithm between languages cannot change either.

### Complexity

- Time: O(r c + r log b) per validate or decide, r rows, c rule columns, b drift bins — each value check reads each row once per rule column with O(1) work (hash lookups for allowed values and dimension keys, a bounded parse for integers and dates); `unique` builds one map per rule; drift places each value with a binary search over the edges.
- Space: O(r + d) for r rows and d dimension keys — the previous batch, the key sets, and the maps and row lists built while checking one batch.

### Trade-offs

- One pass per rule is simple and easy to audit. A columnar engine would instead compute every check of a column in one scan, which matters for wide tables with many rules on the same column.
- Rounding outward for row counts never refuses a batch for a fraction of a row, at the cost of a looser bound on small batches; exact rational bounds are stricter and refuse, for example, any change at all for a previous batch of 7 rows at 10%.
- The zero-share replacement keeps every bin in the sum and makes an empty bin very visible: a bin that empties completely adds roughly `share * ln(share / 0.0001)`. Leaving such bins out, as the arXiv paper does for empty current bins, avoids that jump but hides a category that vanished.
- Comparing with the previous published batch catches sudden changes and follows slow ones. A fixed reference batch catches slow drift, but needs to be refreshed by hand when the data legitimately changes.
- Quarantine keeps good rows flowing, at the risk of publishing a batch with a hole in it. A limit on the share of rows set aside is the usual safeguard.

### Pitfalls and edge cases

- Null is the empty string only. A space is a value, so it passes `not-null` and fails `type`.
- Only `not-null` fails nulls; `range` also skips values that are not integers. Counting those twice makes one bad value appear under two rules.
- Integers: an optional minus and 1 to 15 digits, leading zeros allowed. Library parsers accept `+3`, spaces or `1_000`, depending on the language, and must not be used unchecked.
- Dates: 1900 and 2100 are not leap years, 2000 is; November has 30 days; `0000` is not a year.
- The report follows the order rules were added and the order a rule lists its columns, not the order of the batch's columns or of the rule ids, and leaves out passing columns.
- `failingRows` lists a row once even when it fails in several columns.
- `unique` fails every copy, skips keys with a null part, and compares column by column: joining the values into one string makes `ab`+`c` equal to `a`+`bc`, and any separator fails when a value can contain it.
- `references` reads the dimension at check time, skips nulls, and is refused for a dimension never loaded.
- Row counts round outward. With no previous batch the rule passes; an empty previous batch is still a previous batch, and allows only an empty batch.
- Drift: a value equal to an edge belongs to the higher bin; shares divide by the counted integers, not the rows; a zero share becomes `0.0001`; the threshold is reached at equality; the text has exactly four decimals.
- Freshness uses the newest event, not the oldest or the last row; a lag equal to the limit passes; future events pass; no event time fails.
- The gate: every rule blocks by default; batch rules cannot quarantine; a blocked batch publishes nothing, sets nothing aside and leaves the previous batch alone; batch rules see the rows left after quarantine; the previous batch becomes those rows, not the whole input.

### Language notes

- Integer and date parsing is written by hand in every reference, comparing characters with `'0'` and `'9'`. Python's `int()`, TypeScript's `Number()`, Java's `Integer.parseInt`, Kotlin's `toInt()`, Go's `strconv.Atoi` and Rust's `parse::<i64>()` each accept some text the statement refuses (a leading `+` in all of them, underscores or spaces in some), so they are only called after the hand check.
- The logarithm is `math.log` in Python, `Math.log` in TypeScript and Java, `ln` in Kotlin, `math.Log` in Go and `f64::ln` in Rust; the results can differ in the last bit, which is why the rounding is checked against ties in a content test.
- Times reach 10^15, so they are `long` in Java and Kotlin, `int64` in Go and `i64` in Rust; integers in rows are parsed as 64-bit too. TypeScript's numbers hold them exactly, since 10^15 is below 2^53.
- The unique key is a tuple in Python. TypeScript, Java, Kotlin and Go use a string built with a length prefix for each part (`3:abc1:d`), which cannot collide; Rust uses the vector of the key's values, `Vec<&str>`, as the map key.
- `setTime` returns nothing: `None`, `void`, `Unit`, no result in Go and `()` in Rust.

## Further reading

- C. J. Potgieter, C. van Zyl, W. D. Schutte and F. Lombard, ["The Population Resemblance Statistic: A Chi-Square Measure of Fit for Banking"](https://arxiv.org/abs/2307.11878), arXiv 2307.11878, version 2, 2023: equation (1) defines the population stability index over B bins, equation (2) the symmetric Kullback-Leibler divergence it estimates, and the paper discusses why fixed rule-of-thumb thresholds behave differently for small and large samples.
- S. Kullback and R. A. Leibler, ["On Information and Sufficiency"](https://doi.org/10.1214/aoms/1177729694), The Annals of Mathematical Statistics 22(1), 1951, pages 79 to 86: the information measure that the arXiv paper above names as the basis of the index.
- G. Klyne and C. Newman, [RFC 3339, "Date and Time on the Internet: Timestamps"](https://www.rfc-editor.org/rfc/rfc3339), IETF, 2002: the `full-date` format (section 5.6), the number of days in each month (section 5.7) and the leap-year rule (Appendix C).
