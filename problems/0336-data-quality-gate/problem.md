# Data Quality Gate

## Statement

Build `QualityGate`, the check that runs between a data pipeline and the tables people read. A batch of rows arrives, from a file, an export or another team's system, and before it is published the gate asks: is this batch good enough? The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a quality check?** A check is a rule about the data that you can test mechanically: "every order has a customer", "the status is one of `new`, `paid`, `shipped`", "an age is between 0 and 120". A check that fails does not fix anything; it tells you, early, before a wrong number reaches a report. Some checks look at one value at a time, some at the whole batch, and some compare the batch with the one before it.

**Rules as data.** The checks are not written as code for each column. They are *rules*: a name, the kind of check, the columns it applies to and its parameters, all given as data. The same gate can then guard any table, and the list of rules can be reviewed like configuration.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 60, level 3 by 90 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `QualityGate(columns)`: creates a gate for batches whose rows have these columns, in this order. Column names are distinct.
- A **batch** is a list of rows, and a **row** is a list of strings, one per column, in the order of `columns`. Rows are numbered from `0` in the order of the batch.
- A **null** is the empty string `""`, and only the empty string: a value of spaces is not null.
- Rule ids, check names, column names and parameters are compared exactly, case included.
- Each level's section describes the methods it adds and their parameters.

## Output

A **report** is a list of findings, one for each rule and column that failed; a check that passes is not listed. A finding is a list of strings that starts `[ruleId, column, observed]`, where `observed` is a number written in decimal unless a level says otherwise. Findings follow the order in which the rules were added, and within a rule the order of its columns as the rule lists them. Row numbers are returned ascending.

## Level 1: Row checks

- `addRule(ruleId, check, columns, params)`: adds a rule and returns `true`. It returns `false`, and adds nothing, when `ruleId` is already used, when `check` is not a known check name, or when a column is not one of the gate's columns.
- `validate(rows)`: runs every rule over the batch and returns the report. Validating changes nothing in the gate.
- `failingRows(rows, ruleId)`: the numbers of the rows that fail the rule in at least one of its columns, each once; `[]` for an unknown rule.

The checks of this level look at one value at a time. A rule applies its check to each of its columns separately, and its finding for a column has `observed` = the number of rows whose value in that column fails.

| `check` | `params` | A value fails when |
|---------|----------|--------------------|
| `not-null` | `[]` | it is null |
| `type` | `["int"]` or `["date"]` | it is not null and is not a valid integer or date (below) |
| `allowed` | the allowed values | it is not null and is not one of `params` |
| `range` | `[min, max]`, two integers with `min <= max` | it is a valid integer and is below `min` or above `max`; both bounds are allowed |

**Nulls.** Only `not-null` looks at nulls. Every other check passes a null: whether a value may be missing is a separate question, asked by its own rule. In the same way, `range` passes a value that is not an integer at all, because that is the job of a `type` rule.

**Integers.** An optional `-` followed by 1 to 15 digits `0`-`9`, and nothing else: `-0` and `007` are integers; `+3`, ` 5`, `1.0` and `1e3` are not.

**Dates.** Exactly `YYYY-MM-DD`: four digits, a dash, two digits, a dash, two digits, naming a real day. The year is from `0001` to `9999` and the month from `01` to `12`. April, June, September and November have 30 days, February has 28, or 29 in a leap year, and the other months have 31. A year is a leap year when it is divisible by 4, except a year divisible by 100, unless it is also divisible by 400: 2024 and 2000 are leap years, 2023 and 1900 are not. The format is the `full-date` of RFC 3339 (section 5.6), and the leap-year rule is the one in its Appendix C; this problem also leaves out the year 0000.

### Example 1

<!-- case: ex1 -->

The second `r1` and a rule on the unknown column `phone` are refused. `r1` checks two columns, so it can have two findings: one null `id` and two null `email`s. `shipped` and `PAID` are not allowed values, since the comparison is exact. The ages `-1` and `130` are out of range; the null age is not checked. `failingRows` for `r1` lists rows 1, 2 and 3: row 2 has no id, and rows 1 and 3 have no email.

### Example 2

<!-- case: ex2 -->

`1.5` and `+3` are not integers, while `007` and `-7` are. `2024-02-29` is a real day, but 2023 is not a leap year, there is no month 13, April has 30 days, and there is no year 0. The null values pass both rules.

## Level 2: Dataset checks

Some problems are invisible in a single row. Two rows can each look fine and still describe the same order twice, and an order can name a customer that does not exist.

- `loadDimension(name, keys)`: stores a set of valid keys under `name`, such as the ids of a customer table, replacing a set already stored under that name. It returns the number of distinct keys. Rules always read the set as it is when they run.
- `setPreviousBatch(rows)`: tells the gate what the previous batch was; it returns its number of rows. The latest call wins.

New checks for `addRule`:

| `check` | `columns` | `params` | Fails when |
|---------|-----------|----------|------------|
| `unique` | the key columns, one or more | `[]` | two or more rows have equal values in **all** the key columns |
| `references` | exactly one | `[dimensionName]` | a value is not null and is not a key of that dimension |
| `row-count` | none, `[]` | `[tolerance]`, an integer percentage from 0 to 100 | the batch has too many or too few rows compared with the previous batch |

- **unique** compares the key column by column, so `["ab", "c"]` and `["a", "bc"]` are different keys. A row with a null in any key column is not checked. When a key appears more than once, **every** row with that key fails, the first one included: the gate cannot know which copy is right. The finding is `[ruleId, keyColumns, observed]`, where `keyColumns` is the key column names joined with `+` (`order+line`) and `observed` the number of failing rows. `failingRows` lists them.
- **references** is checked like a level 1 rule. `addRule` returns `false` for a dimension that has not been loaded.
- **row-count**: let `P` be the number of rows of the previous batch and `t` the tolerance. The allowed range is from `floor(P * (100 - t) / 100)` to `ceil(P * (100 + t) / 100)`, both included: the bounds are rounded outward, so that a small batch is never refused for a fraction of a row. With no previous batch the rule passes. Its finding is `[ruleId, "", count]`, with the number of rows in the batch. It fails no single row, so `failingRows` returns `[]` for it.

### Example 1

<!-- case: ex3 -->

`c2` is listed twice, so the dimension has 2 keys, and a rule on the unknown dimension `products` is refused. Rows 0 and 2 share the key `o1`, `1`: both fail. Rows 4 and 5 look alike, but their `line` is null, so they are not checked. `c3` is not a customer; the null customer is not checked.

### Example 2

<!-- case: ex4 -->

With no previous batch the count passes. After a previous batch of 7 rows, 10% allows from `floor(6.3) = 6` to `ceil(7.7) = 8` rows: 5 and 9 fail, 6 and 8 pass.

## Level 3: Drift and freshness

A batch can pass every rule and still be wrong: if the ages in today's batch are mostly over 50 while yesterday's were mostly under 30, something upstream probably broke. And a batch can be perfect but old.

- `setTime(now)`: sets the gate's clock, a number such as seconds; the gate never reads a real clock. Before any call the time is `0`.

New checks for `addRule`:

| `check` | `columns` | `params` |
|---------|-----------|----------|
| `drift` | exactly one, holding integers | `[threshold, edge1, ..., edgeK]`: a decimal threshold with at most 4 places, then K >= 1 integer edges in increasing order |
| `freshness` | exactly one, holding event times as integers | `[maxLag]`, an integer >= 0 |

**Drift** compares how the column's values are spread in this batch with how they were spread in the previous batch, using the **population stability index** (PSI).

1. The edges cut the integers into K + 1 bins: bin 0 holds the values below `edge1`, bin i holds `edge_i <= v < edge_(i+1)`, and bin K the values from `edgeK` up. A value equal to an edge belongs to the bin that starts at it.
2. In each batch, only the values that are valid integers count; nulls and other text are left out. If either batch has no counted value, or there is no previous batch, the rule passes.
3. The *share* of a bin is the number of counted values in it divided by the number of counted values in its batch. A share of exactly 0 is replaced by `0.0001`, so that every bin takes part and nothing is divided by zero.
4. With `a_i` the shares of this batch and `e_i` those of the previous batch, `PSI = sum over all bins of (a_i - e_i) * ln(a_i / e_i)`, where `ln` is the natural logarithm. Every term is zero or positive, so PSI is 0 when the spreads are equal and grows as they move apart.
5. PSI is rounded to 4 decimal places, the nearest multiple of `0.0001` (no case lands on a half). The rule fails when the rounded PSI is **at least** the threshold. Its finding is `[ruleId, column, psi]`, the rounded PSI written with exactly four decimals: `0.2773`, `0.0032`, `4.2570`.

This is the population stability index as defined in equation (1) of the Population Resemblance Statistic paper on arXiv (2307.11878), a sum of `(share now - share before) * (log share now - log share before)` that estimates the symmetric Kullback-Leibler divergence. That paper leaves out a bin whose current share is zero; this problem replaces any zero share with `0.0001` instead.

**Freshness** asks whether the newest event in the batch is recent enough. The newest event is the largest valid integer in the column. With `lag = now - newest`, the rule fails when `lag > maxLag`, and its finding is `[ruleId, column, lag]`. An event after `now` gives a negative lag, which passes. A batch with no valid event time has no evidence of being fresh: the rule fails with `observed` = `"none"`.

Both checks judge the whole batch, so `failingRows` returns `[]` for them.

### Example 1

<!-- case: ex5 -->

The first validation has no previous batch, so drift passes. The previous batch then has 2, 6, 8 and 4 ages in the bins below 18, 18 to 29, 30 to 49, and 50 up: shares 0.1, 0.3, 0.4 and 0.2. The next batch has shares 0.05, 0.15, 0.4 and 0.4, and `PSI = (0.05 - 0.1) ln 0.5 + (0.15 - 0.3) ln 0.5 + 0 + (0.4 - 0.2) ln 2 = 0.2773`, above the threshold 0.1. A batch of 10 ages with the same shares as before has PSI 0, and a batch whose shares moved a little stays below 0.1.

### Example 2

<!-- case: ex6 -->

At time 10000 the newest event, 9000, is 1000 old, within 3600. At 20000 the lag is 11000. A batch whose event times are null or not integers, and an empty batch, fail with `none`.

## Level 4: The gate

A finding is only information. The gate turns findings into a decision: publish the batch, publish it without its bad rows, or hold it back.

- `setAction(ruleId, action)`: sets what a failure of the rule does, and returns `true`. Every rule starts as `"block"`.
  - `"warn"`: the failure is reported and the batch can still be published.
  - `"quarantine"`: the rows that fail the rule are set aside and the rest can be published. Only a rule that fails rows can quarantine: `not-null`, `type`, `allowed`, `range`, `unique` and `references`.
  - `"block"`: a failure holds back the whole batch.
  - It returns `false`, and changes nothing, for an unknown rule, an unknown action, or `"quarantine"` on a `row-count`, `drift` or `freshness` rule.
- `decide(rows)`: decides about the batch in two passes.
  1. The row rules (`not-null`, `type`, `allowed`, `range`, `unique`, `references`) run on **all** the rows. Every row that fails at least one rule whose action is `"quarantine"` is set aside, once.
  2. The batch rules (`row-count`, `drift`, `freshness`) run on the rows that are **left**, because those are what would be published.
  3. If any failing rule's action is `"block"`, the decision is `"block"`: nothing is published and nothing is set aside. Otherwise the decision is `"publish"`: the rows left are published, and they become the previous batch for `row-count` and `drift`. A blocked batch does not change the previous batch.
  4. The answer starts with `[decision, published, setAside]`: the decision, the number of rows published and the number set aside, both `"0"` on a block. Then come the findings of every failing rule, in the order the rules were added, each with the rule's action as a fourth string: `[ruleId, column, observed, action]`.
- `quarantined()`: the numbers of the rows the last `decide` set aside; `[]` before any `decide` and after a block.

### Example 1

<!-- case: ex7 -->

A `row-count` rule cannot quarantine. Row 1 has no id and row 3 an amount of 5000: both are quarantine rules, so the two rows are set aside. Row 2 has no email, which only warns. Three rows are published. The next batch has one row, within 50% of the three published before, and nothing fails.

### Example 2

<!-- case: ex8 -->

The row with the time `later` is set aside, and freshness runs on the two rows left, whose newest event, 990, is 10 old. Those two rows become the previous batch, so a batch of 2 passes the row count with no tolerance and a batch of 3 is blocked. Being blocked, it does not become the previous batch: the next batch of 2 passes again.

## Constraints

- `1 <= columns.length <= 10`; names are 1 to 20 characters from `a`-`z`, `0`-`9` and `_`.
- At most 50 rules; every row of a batch has exactly `columns.length` values of 0 to 30 printable ASCII characters (codes 32 to 126).
- Rule parameters fit their check, as each level describes: the right number of columns and parameters, integers where integers are named, at most 10 drift edges.
- `0 <= now <= 10^15`.
- At most 200 calls per test, at most 1000 rows per batch and at most 1000 keys per dimension.

## Follow-ups

- Nothing stops a quarantine from setting aside most of a batch. How would you add a limit on the share of rows set aside, and which rounding would you choose for it?
- Drift here compares with the previous batch, so a slow change moves the baseline a little every day and is never caught. What would you compare with instead?
- PSI depends on the bins. How would you choose the edges for a column you know nothing about, and why do equal-width bins work badly for skewed data?
- A rule that fails every day is soon ignored. How would you record how often each rule fails, so that a noisy rule can be fixed or retired?

## Hints

### Hint 1

Store each rule as a small record (id, check, columns, params, action) in a list, plus a map from id to rule so that duplicates are easy to refuse. `validate` is then a loop over the list: for each rule, for each of its columns, count the rows whose value fails, and add a finding when the count is not zero.

### Hint 2

Write one function `fails(rule, value)` with one branch per value check, and let the null test come first: `not-null` fails exactly the empty string, and every other check returns "passes" for it. Parse integers and dates by looking at each character instead of calling a library parser, which accepts signs, spaces or other forms the statement does not allow.

### Hint 3

For `unique`, build a map from the whole key, as a tuple or a list, to the rows that have it. A key made by gluing the values together into one string can make two different keys equal unless the separator can never appear in a value. Rows in groups of two or more fail.

### Hint 4

For `row-count`, keep the bounds in integers: `floor(a / b)` for non-negative numbers is integer division, and `ceil(a / b)` is `(a + b - 1) / b` with integer division.

### Hint 5

For drift, count the values per bin in each batch, turn counts into shares, replace the zero shares, and sum the terms. To round to four places, compute `floor(psi * 10000 + 0.5)` as an integer number of ten-thousandths; compare it with the threshold read in the same units, and print it as the integer part, a dot and four digits.

### Hint 6

At level 4, `decide` first collects the rows set aside by quarantine rules into a set, builds the list of rows left, and only then runs the batch rules on that list. Gather all findings with their actions before you decide, and change the previous batch and the quarantined rows only when the decision is to publish.
