# Query Planner

## Statement

Build `QueryPlanner`, the part of a relational database that decides *how* to run a query. A query says what result you want; there are many ways to compute it, and on large tables the fastest way can be thousands of times faster than the slowest. The planner turns the query into a *plan*, estimates how many rows each step will produce, and picks the plan it expects to be cheapest. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Tables and queries.** A *table* holds rows, and every row has the same named *columns*: a table `users` with columns `id`, `country_id` and `age` holds one row per user. A query in SQL, the language of relational databases, says which rows and columns you want:

```sql
SELECT users.id FROM users WHERE users.age > 30
```

reads the rows of `users`, keeps those whose `age` is above 30, and returns their `id`. A *join* combines two tables: `FROM orders JOIN users ON orders.user_id = users.id` pairs each order with the user who placed it, the rows whose `user_id` equals the user's `id`.

**What a query plan is.** A database does not run the text of a query. It turns it into a *plan*: a tree of small operators, each of which takes rows from its children and passes rows up to its parent. The rows flow from the leaves, which read tables, up to the root, which returns the result. This problem uses four operators:

| Operator | Does |
|----------|------|
| `scan t` | reads every row of table `t` |
| `filter` | passes on the rows of its child that satisfy all its conditions |
| `join` | pairs the rows of its two children that satisfy its join condition |
| `project` | keeps the selected columns of each row |

Level 1 parses a small part of SQL and builds the plan in the order the query is written. Level 2 estimates the number of rows of each operator from table statistics. Level 3 chooses the order of the joins, and level 4 chooses how to read each table and how to run each join.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `QueryPlanner()`: creates a planner with an empty *catalog*, the list of known tables.
- A **name** of a table or a column has 1 to 20 characters: small letters `a` to `z`, digits and `_`, starting with a small letter.
- A **query** is a string of at most 300 printable ASCII characters (codes 32 to 126).
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the catalog return a *status*, a string: `"ok"` when the change was made, or one of the error words the level lists, in which case **nothing has changed**. The methods that plan a query return the plan as a list of lines, described in level 1; when the query is invalid, the list holds one line instead, `"error: <code>"` followed by a detail where the level gives one, such as `"error: unknown-table books"`.

## Level 1: Parse and plan in written order

**The query language.** A query follows this grammar, where `*` after a part means "zero or more times" and `?` means "optional":

```text
query     := "SELECT" columns "FROM" name join* where?
columns   := "*" | column ("," column)*
join      := "JOIN" name "ON" column "=" column
where     := "WHERE" condition ("AND" condition)*
condition := column ("=" | "<" | ">") number
column    := name "." name
```

The query is read as a list of *tokens*, separated by any number of spaces, which are otherwise ignored:

- a *word*: a letter or `_`, then letters, digits and `_`. The words `SELECT`, `FROM`, `JOIN`, `ON`, `WHERE` and `AND`, in capital letters exactly, are the *keywords*; every other word is a name. A word in the grammar's `name` place must not be a keyword.
- a *number*: 1 to 9 digits, possibly preceded by `-` with no space in between, kept as written (`007` stays `007`).
- one of the symbols `*` `,` `.` `=` `<` `>`.

Any other character, or a list of tokens that does not follow the grammar, is a syntax error. A column is always written with its table, as `table.column`, and a table appears at most once in a query.

**Checks.** An invalid query gives a one-line plan. The checks run in this order, and the first failure is reported. The two table checks go through the tables in the order written, and for each table the catalog check comes first:

| Error line | When |
|------------|------|
| `error: syntax` | the query does not follow the grammar |
| `error: unknown-table <t>` | a table of the query is not in the catalog |
| `error: duplicate-table <t>` | a table appears in the query a second time |
| `error: unknown-column <t>.<c>` | a column whose table is not one of the query's tables, or which its table does not have; columns are checked in the order written: the selected columns, then the two columns of each `ON`, then those of `WHERE` |
| `error: bad-join <t>` | the `ON` condition of `JOIN <t>` does not compare a column of `<t>` with a column of a table that comes before `<t>` in the query |

**The plan.** Build the plan of a valid query in the order it is written:

1. Each table gets a *subtree*: `scan t`, with a `filter` right above it when `WHERE` has conditions on `t`. The filter holds all of them, in the order written. Putting each condition directly above the table it reads, instead of after the joins, is called *predicate pushdown*: it throws rows away as early as possible.
2. The plan starts as the subtree of the table after `FROM`. Each `JOIN`, in the order written, makes a `join` whose left child is the plan so far and whose right child is the subtree of the new table.
3. A `project` with the selected columns is the root.

The lines of a plan list its nodes from the root down, each line indented by two spaces more than its parent's, a node's left child with its whole subtree before its right child:

| Node | Line |
|------|------|
| project | `project *`, or `project` and the selected columns as written, separated by `", "` |
| join | `join a.x = b.y`, with the column of the left child's tables first |
| filter | `filter` and its conditions separated by `" AND "`, each written `t.c > 5`, with one space around the operator and the number as written |
| scan | `scan t` |

- `addTable(table, columns)`: adds a table with its columns (1 to 10 different names, in this order). Statuses: `"duplicate"` when the table is already in the catalog.
- `logicalPlan(sql)`: the plan of the query, or its error line.

### Example 1

<!-- case: ex1 -->

The second `addTable("users", ...)` is refused and leaves the first one in place. The query on `users` alone gets a filter above its scan. In the third query, `orders` is joined to `users`, and then the result to `countries`, as written. Each condition sits above the scan of its table. The `ON` condition of `countries` is written `countries.id = users.country_id`, but the plan writes the column of the left side, `users`, first.

### Example 2

<!-- case: ex2 -->

`>` needs a number after it. `shipments` is not in the catalog. `users` has no column `name`. The `ON` condition names `countries`, which is not a table of this query, so the column check fails before the join check.

## Level 2: Estimate row counts

A planner cannot run every plan to see which is fastest; it *estimates* how many rows each node produces, from *statistics* that the database keeps about each table: the number of rows, and the number of *distinct values* in each column. Classic planners combine them under two assumptions:

- **Uniformity**: each distinct value of a column appears equally often. So `users.plan = 2`, on a column with 3 distinct values, keeps one row in 3.
- **Independence**: conditions on different columns are unrelated, so their fractions multiply. In reality they often are related (city and country), which is the main reason why estimates go wrong.

For a condition that is not an equality, such as `age > 30`, this planner assumes that one row in 3 passes: the planner that Selinger and colleagues described in 1979 used the same fraction when it could not interpolate between the lowest and the highest value of the column.

- `analyze(table, rows, distinct)`: records the statistics of a table: its number of rows, and the number of distinct values of each column, in the order of its columns. Statistics recorded again replace the old ones. Statuses, in this order: `"unknown-table"`; `"bad-stats"` when `distinct` does not have one count per column, `rows` is below 1, or a count is below 1 or above `rows`.
- `estimate(sql)`: the plan of level 1, with ` (rows=N)` added at the end of every `scan`, `filter` and `join` line, `N` being the estimated number of rows that node produces. One more error, checked after those of level 1: `error: no-stats <t>`, for the first table of the query, in the order written, without statistics.

**The estimates.** Write `round(N / D)` for the whole number nearest to `N / D`, rounding a half up (2.5 gives 3), and **at least 1**: a planner never estimates an empty result.

| Node | Estimate |
|------|----------|
| `scan t` | the rows of `t` |
| `filter` over `t` | `round(rows of t / D)`, where `D` multiplies one *divisor* per condition: the distinct values of the column for `=`, and 3 for `<` or `>` |
| `join` | `round(N / D)`. `N` multiplies, for every table below the join, its estimate: the filter's when the table has a filter, else the rows of the table. `D` multiplies, for every join condition below the join and its own, the larger of the distinct values of its two columns |

The join rule assumes that every value of the column with fewer distinct values also appears in the other column. Note what it does **not** do: it never uses the estimate of a join below it, and it never rounds between steps. The estimate of a join depends only on the set of tables below it, not on the order in which they were joined, which level 3 relies on. Distinct values are always those of the whole table, even after a filter.

Compute with whole numbers only: `round(N / D)` is `(2 * N + D) / (2 * D)` with integer division, then at least 1. A floating-point division can round a quotient just below a whole number up to it, and some languages' built-in rounding sends 2.5 to 2.

**Bounds.** Statistics given to `analyze` hold at most 10^9 rows. For every query that is estimated, the product of the row counts of its tables is at most 10^15, and so is the product of the divisors of its conditions for each table, and the product of the divisors of its join conditions. So every number of this level and the next two, for the chosen plan or any other, is below 2^53: exact in a 64-bit integer and in a JavaScript number.

### Example 1

<!-- case: ex3 -->

`users` has 20000 rows and its column `plan` 3 distinct values, so `plan = 2` keeps `round(20000 / 3) = 6667` rows. The second query has two conditions: `age > 60` divides by 3 and `country_id = 7` by 50, so the filter keeps `round(20000 / 150) = 133`. `orders` has no statistics. The last two `analyze` calls give 3 counts for 4 columns, then a count above the number of rows.

### Example 2

<!-- case: ex4 -->

With `plan = 1` the filter keeps 6667 users. The join multiplies 200000 orders by those 6667 users and divides by the larger distinct count of `orders.user_id` (20000) and `users.id` (20000): `round(200000 * 6667 / 20000) = 66670`. In the second query, `orders.total > 500` keeps `round(200000 / 3) = 66667` orders and `region = 2` keeps 10 of the 50 countries. The top join covers all three tables: `66667 * 20000 * 10`, divided by 20000 for the first join condition and by 50 for the second, gives 13333.4, so 13333.

## Level 3: Choose the join order

The result of a query does not depend on the order of its joins, but the work does. Joining 200000 orders with 20000 users first produces a large intermediate result that the next join has to read; joining the 10 chosen countries with their users first produces only 4000 rows, which then meet the orders. The planner chooses the order.

**Left-deep plans.** This planner considers *left-deep* plans: the right child of every `join` is the subtree of one table, as in level 1, so a plan is fully described by its *join order*, the list of its tables from the first one to the last one joined. A table may be added only when it has a join condition with a table already joined, so the planner never pairs every row of one side with every row of the other (a *Cartesian product*). The join conditions are those of the `ON` clauses, wherever they are written.

**The cost.** The cost of a plan is the sum of the estimates of all its `join` nodes: the number of rows that each join hands to the next operator. A plan with one table costs 0.

- `optimize(sql)`: the plan of the join order with the lowest cost, written as in level 2, except that every `join` line ends with ` (rows=N cost=C)`, where `C` is the cost of the subtree under that join line, that join included. Each join line writes the column of the tables already joined first. On a tie, the planner takes the join order whose list of table names comes first, comparing the lists name by name, and names by the codes of their characters.

With 4 tables there are at most 24 orders, few enough to try them all, but each extra table multiplies the number of orders. The classic technique, from the same 1979 planner, is *dynamic programming over subsets*: the cheapest left-deep plan of a set of tables ends with some table `t`, and the part before `t` must be the cheapest plan of the set without `t`. So the best plan of each set of 2 tables comes from the best plans of single tables, each set of 3 from the sets of 2, and so on: one entry per subset instead of one per order.

### Example 1

<!-- case: ex5 -->

The statistics are those of the level 2 examples. Written order joins `orders` and `users` first (66667 rows), then `countries` (13333): cost 80000. The planner starts with the 10 chosen `countries`, joins `users` (4000 rows, cost 4000) and then `orders` (13333 rows, cost 4000 + 13333 = 17333). The second query has two orders of the same cost, 200000; `orders` comes before `users` by name, so it goes first.

### Example 2

<!-- case: ex6 -->

Starting from the 67 authors of country 7 gives 335 books, and then 2513 loans: cost 2848. Starting from `loans` would first produce 300000 rows. A query on one table has no join and so no cost.

## Level 4: Access paths and join methods

So far a table is always read whole and a join is just a join. A real planner also chooses an *access path* for each table and a *method* for each join, and it compares them with a cost model. This planner's costs count rows read or handled; it is a simplified model, not that of any particular database.

**Indexes.** An *index* on a column lets the database find the rows with a given value without reading the whole table, like the index of a book. But each row found through an index is fetched on its own, and such a *random read* costs more than reading the next row of a full scan. In this model it costs 4 reads.

- `addIndex(table, column)`: adds an index. Statuses, in this order: `"unknown-table"`; `"unknown-column"` when the table has no such column; `"duplicate"` when the index exists.

**Access paths.** Each table is read in one of these ways:

| Path | Usable when | Rows read | Cost |
|------|-------------|-----------|------|
| full scan | always | the rows of the table | the rows of the table |
| index scan on condition `t.c = v` | `t.c` has an index; only `=` conditions | `m = round(rows of t / distinct values of t.c)`, as in level 2 | `4 * m` |

The planner takes the cheapest path; on a tie, the full scan, then the index on the condition written first. The rows the table hands on are the estimate of level 2 either way: the filter's estimate, over all its conditions, or the rows of the table without conditions.

**Join methods.** A join whose left input has `L` rows (the estimate of level 2 for the tables already joined) and whose right input is a table with access cost `A` and estimate `E` runs as one of:

| Method | How | Cost |
|--------|-----|------|
| nested loop | for each left row, read the right table again | `L * A` |
| hash join | read the right table once, put its `E` rows in a hash table, then look up each left row | `A + E + L` |

The planner takes the cheaper method; on a tie, the nested loop. The cost of a plan is the access cost of its first table plus the cost of each of its joins, and the planner chooses the join order with the lowest cost, with the tie rule of level 3. A nested loop is cheap when the left side is tiny, and a hash join wins as soon as the left side has more than a few rows.

- `explain(sql)`: the chosen plan, with these lines:

| Node | Line |
|------|------|
| project | as in level 1 |
| join | `nested loop a.x = b.y (rows=N cost=C)` or `hash join a.x = b.y (rows=N cost=C)`, with `C` the cost of the subtree under that line: the cost of its left subtree plus the cost of this join |
| full scan | `full scan t (rows=R cost=R)`, with `R` the rows of the table, under `filter <all its conditions> (rows=E)` when the table has conditions |
| index scan | `index scan t.c = v (rows=m cost=C)`, the condition written as in a filter, under `filter <its other conditions> (rows=E)` when the table has other conditions |

Because a nested loop reads its right table once per left row, its cost is not the sum of the costs of its children.

### Example 1

<!-- case: ex7 -->

`plan` has 3 distinct values, so its index would fetch 6667 rows at 4 reads each, more than the 20000 of a full scan: the planner reads the whole table. The index on `country_id` (50 values) fetches 400 rows for 1600, and the other two conditions stay in a filter whose estimate, 44, covers all three conditions. `age` has no index.

### Example 2

<!-- case: ex8 -->

Joining all orders with all users: a hash join costs 20000 + 20000 + 200000, plus the 200000 of reading `orders` first, 440000, where a nested loop would cost 200000 times 20000. Starting from `users` costs 440000 too, and `orders` comes first by name. In the second query the filter keeps a single country, so a nested loop that reads `users` once costs 50 + 1 * 20000 = 20050, less than a hash join.

## Constraints

- At most 200 calls per test, at most 20 tables in the catalog, at most 4 tables in a query.

## Follow-ups

- Real tables are skewed: a few values are very common. How would a histogram, or a list of the most common values, change the estimate of `t.c = v`?
- The independence assumption fails on correlated columns (`city` and `country`). How could the database detect it, and what would it store?
- An index on the join column of the right table allows an *index nested loop*: for each left row, look up its partners through the index. What would it cost in this model, and when would it beat a hash join?
- *Bushy* plans join two joined results with each other. When can a bushy plan beat every left-deep one, and how does the dynamic programming change?
- The planner that Selinger and colleagues described in 1979 also keeps, for each subset, the cheapest plan for each useful row order ("interesting orders"), so that a later merge join or `ORDER BY` needs no sort. How many entries does the table then hold?

## Hints

### Hint 1

Split level 1 into three steps, each easy to test on its own: a tokenizer that turns the text into words, numbers and symbols; a parser that follows the grammar token by token and records the selected columns, the tables, the join conditions and the `WHERE` conditions; and a checker that runs the checks in the order of the table. Only then build the plan.

### Hint 2

Build the plan as nested nodes, then print it with one recursive function that takes a node and a depth. A join's line needs its condition with the left side's column first: you know which tables are on the left, so swap the two columns when the first one belongs to the new table.

### Hint 3

For level 2, write one function that estimates a set of tables: multiply their filtered estimates, divide once by the divisors of the join conditions whose two tables are both in the set. Every join node calls it with the tables below it. Keep the rounding in one helper and test it on 2.5.

### Hint 4

For level 3, keep a dictionary from a set of tables (a bit mask works well with at most 4 tables) to the best (cost, order) found for it. Fill it by size: for each set `S` you have, and each table `t` outside it that has a join condition with a table of `S`, the candidate for `S + t` costs `cost(S) + estimate(S + t)`.

### Hint 5

Compare candidates by cost first and then by their list of names. Because the estimate of `S + t` does not depend on the order inside `S`, the best order of `S + t` that ends with `t` always starts with the best order of `S`, ties included: appending the same name to two lists keeps their order.

### Hint 6

For level 4 nothing about the search changes: only the cost of adding `t` to `S`, which is now the cheaper of `L * A` and `A + E + L` with `L` the estimate of `S`, and the cost of a single table, which is its access cost. Compute each table's access path once, before the search.
