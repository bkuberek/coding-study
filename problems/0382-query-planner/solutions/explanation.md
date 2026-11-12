# Query Planner: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| subset-dp | optimal | O(q) to parse and check; O(2^k k^2) to choose a plan | O(2^k k) | default answer; one table per subset of tables serves both cost models |

Here `q` is the length of the query and `k` the number of its tables (at most 4).

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | A tokenizer, a parser that follows the grammar, the checks in their order, and a printer for left-deep plans | the catalog (table to its columns); a checked query: tables in written order, the conditions of each table, one join edge per `JOIN` |
| 2 | Statistics, one rounding helper, an estimate per table and one per set of tables | the statistics (rows and distinct counts per table) |
| 3 | A search over join orders by dynamic programming over subsets | a table from a subset of tables to its best (cost, order) |
| 4 | An access path per table and a join method per step; the search gets a second cost function | the set of indexes |

The early choice that keeps the later levels cheap is to print a plan from a *join order* (a list of tables) instead of from the parse: level 1 prints the written order, and levels 3 and 4 print the order they choose with the same code. The second is to estimate a *set* of tables rather than a node: because the estimate of a join depends only on the tables below it, levels 3 and 4 can look it up for a subset without building any plan.

## Approach: subset-dp (Recursive-descent parser and dynamic programming over subsets of tables)

### Intuition

A query has few tables but many possible plans, and every plan has the same result, so the planner is a search for the cheapest one under a cost model. The search is small if the cost of a plan splits into parts that depend only on which tables are already joined, not on how: the estimate of a set of tables is a product over its tables and its join conditions, so it is the same for every order of the set. Then the best way to finish a set by adding table `t` last uses the best way to build the set without `t`, which is the principle of optimality behind dynamic programming, and one entry per subset replaces one entry per order.

### Algorithm

1. Level 1: split the text into words, numbers and symbols; walk the grammar token by token, recording the selected columns, the tables, the `ON` pairs and the `WHERE` conditions; any token out of place is `syntax`. Check the tables in written order (catalog, then repeat), the columns in written order, then each `ON`, swapping its two columns when the first belongs to the new table so that every join edge is stored as (earlier column, new column). To print a join order `t1 .. tn`: the project line, then the joins from the last to the first, each indented one step more, then the subtree of `t1` at depth `n`, and the subtree of `tk` (k from 2) at depth `n - k + 2`. A subtree is `scan t`, under `filter` and the table's conditions when it has any.
2. Level 2: `round(N, D) = max(1, (2N + D) div 2D)`. A table's estimate is its rows divided by the product of its condition divisors (distinct count for `=`, 3 otherwise); a set's estimate is the product of its tables' estimates divided by the product of `max(distinct, distinct)` over the join edges inside the set. Every line of level 1 gets the estimate of its node.
3. Level 3: `best[{t}] = (0, [t])` for every table. For sizes 2 to `k`, for every set `S` of the previous size and every table `t` outside `S` with an edge into `S`, the candidate for `S + t` is `(cost(S) + rows(S + t), order(S) + [t])`; keep the smallest candidate, comparing the cost and then the list of names. The answer is `best[all tables]`, printed with each join line's edge written from the joined side.
4. Level 4: the access path of a table is the cheapest of the full scan (its rows) and the index scans of its `=` conditions on indexed columns (`4 * round(rows / distinct)`), the full scan first and the conditions in written order on a tie. The search starts from `(access(t), [t])`, and adding `t` to `S` costs `min(L * A, A + E + L)`, with `L` the estimate of `S`, `A` the access cost of `t` and `E` its estimate, the nested loop on a tie. The printer writes the method, the access path, and the filter of the remaining conditions.

### Correctness

Parsing and checks: each check runs only on queries that passed the earlier ones, in the order the table gives, so the first failing check is the one reported. The parser accepts exactly the grammar, because each function consumes exactly the tokens of its rule and the top level requires the end of the tokens.

Estimates: `(2N + D) div 2D` is `floor(N / D + 1/2)`, which is the nearest whole number with halves rounded up. Every multiplication and the division use whole numbers, so the result is exact; the constraints keep every product below 2^53.

Search, level 3: let `S` be a set and `P` a cheapest valid order of `S` ending with `t`. Its cost is the cost of its prefix `P'` (an order of `S - t`) plus `rows(S)`, which does not depend on `P'`. If some valid order of `S - t` were cheaper than `P'`, or as cheap with an earlier list of names, replacing `P'` with it would give an order of `S` that is cheaper, or as cheap and earlier, since appending the same `t` to two lists of the same length keeps their order. So `P'` is `best[S - t]`, and taking the minimum over every last table `t` finds `best[S]`. The prefix of a valid order is valid: a table added with an edge into the joined set still has it when only later tables are removed.

Search, level 4: the same argument holds, because the cost of adding `t` to `S` depends only on `rows(S)` (an estimate of the set) and on `t`.

### Complexity

- Time: O(q) to parse and check; O(2^k k^2) to choose a plan — the tokenizer and the parser read each character and each token once, and the checks look up each name in a dictionary; the search visits each of the 2^k subsets with each of its `k` possible next tables, and each candidate computes an estimate over at most `k` tables and edges.
- Space: O(2^k k) — one entry per subset, holding a cost and an order of at most `k` names; the parsed query and the catalog are small.

### Trade-offs

- With at most 4 tables, trying all 24 orders is just as fast and easier to get right; the reference uses dynamic programming because it is what a real planner does and because it scales to a dozen tables, where the orders number in the hundreds of millions.
- Restricting the search to left-deep plans without Cartesian products shrinks it and lets nested loops use a table as their inner side, but it can miss a cheaper *bushy* plan, which joins two intermediate results with each other.
- The cost model counts rows. Real planners count pages read and processor work separately, as Selinger and colleagues did with page fetches plus a weight times the calls into the storage system, and they tune the weights to the hardware. The shape of the search does not change.
- Estimates from row counts and distinct counts are cheap to keep but ignore skew and correlation; histograms and multi-column statistics cost more to maintain and fix the commonest errors.

### Pitfalls and edge cases

- `select` in small letters is not a keyword; a condition compares a column with a number only; `- 3` with a space is not a number, and a number is kept as written (`007`).
- A column of a catalog table that is not in the query is `unknown-column`, even when the table exists. The column check runs before the join check, so an `ON` that names such a table fails as `unknown-column`, not `bad-join`.
- Conditions go above the scan of their own table, in the order written; a join line writes the joined side's column first, whatever the query wrote.
- Round half up, at least 1. Python's `round` rounds 2.5 to 2, and floating-point division can turn a quotient just below a whole number into it: use whole numbers. A filter divides once by the product of its divisors, not once per condition, and a join never starts from the estimate of the join below it.
- The join divisor is the larger distinct count of the two columns, not the smaller.
- Statistics are rejected when the list has the wrong length, when `rows` is below 1, or when a count is below 1 or above the rows.
- The cost of a plan counts every join, the last one included; scans are free at level 3. Ties go to the earlier list of names: neither the written order nor a greedy choice gives it.
- An index serves `=` only, and only when it is cheaper than the full scan (a column with few distinct values makes a poor index). The filter above an index scan estimates all the table's conditions from the statistics, not from the rows the index returns.
- A nested loop multiplies the left rows by the right table's access cost; ties between the methods go to the nested loop, and the first table's access cost is part of the plan's cost.

### Language notes

- A subset is a bit mask in Java, Kotlin, Go, Rust and TypeScript and a `frozenset` in Python; with at most 4 tables either is fine, and a mask makes "all sets of size `s`" a loop over integers.
- Comparing (cost, list of names) uses tuple comparison in Python; the other languages compare the costs and then the names one by one, which works because all the orders of a set have the same length.
- Estimates and costs are `long` in Java, `Long` in Kotlin, `int64` in Go and `i64` in Rust. TypeScript numbers are exact below 2^53, which the constraints guarantee, but `Math.floor(a / b)` can still be off by one when `a / b` is just below a whole number; the reference divides with `(a - a % b) / b`, which is exact.
- Rust parameters are owned `String` and `Vec`, as the bridge requires, and the plan helpers borrow the planner immutably; Go returns an error string and a nil plan instead of an exception.

## Further reading

- P. G. Selinger, M. M. Astrahan, D. D. Chamberlin, R. A. Lorie and T. G. Price, "Access path selection in a relational database management system", Proceedings of the 1979 ACM SIGMOD International Conference on Management of Data, 23–34, [doi:10.1145/582095.582099](https://doi.org/10.1145/582095.582099): the System R optimizer. It gives the cost formula `COST = PAGE FETCHES + W * (RSI CALLS)`; the selectivity factors of its Table 1, among them `1 / ICARD` for `column = value` under an even distribution, `1 / MAX(ICARD(column1), ICARD(column2))` for `column1 = column2`, a default of 1/3 for an open-ended comparison it cannot interpolate, and the product of factors for `AND`, which "assumes that column values are independent"; the observation that the cardinality of a join of n relations does not depend on the order; the search for the best order of successively larger subsets, with at most 2^n subsets times the number of interesting orders; the heuristic that delays Cartesian products as long as possible; and the two join methods it considered, nested loops and merging scans, with `C-outer + N * C-inner` as the cost of a nested loop.
