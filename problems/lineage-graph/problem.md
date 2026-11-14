# Lineage Graph

## Statement

Build `LineageGraph`, which records where every column of a data platform comes from. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is lineage?** A data platform is a chain of tables, here called *datasets*: raw tables loaded from other systems, cleaned tables built from them, and reports built from those. When a number in a report looks wrong, the first question is "where does this number come from?", and the second, before changing anything, is "what will this break?". *Lineage* answers both. Column-level lineage goes further than "this table reads that table": it says which **columns** each column is computed from, and how.

**The specs.** Every job that builds a dataset can describe itself as data: for each output column, the input columns it reads and how it uses each one. `revenue.total` is the sum of `order_facts.amount_eur`; `order_facts.amount_eur` is computed from `orders.amount`, and only for rows whose `orders.status` is paid. Put together, those specs form a graph: one node per column, one arrow from each input column to the column computed from it.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `LineageGraph()`: creates an empty graph.
- A **dataset name** and a **column name** are 1 to 20 characters from `a`-`z`, `0`-`9` and `_`. A column is named in full as `dataset.column`, such as `orders.amount`.
- Each level's section describes the methods it adds and their parameters.

## Output

Columns are named in full (`dataset.column`). Lists are sorted by the numeric value of their characters, so that `10` comes before `9`, and `_` before the letters, unless a method states another order; a list of lists is sorted by its first string, then its second, and so on. A method that finds nothing returns `[]`.

## Level 1: Specs and validation

- `addDataset(name, columns, edges)`: declares a dataset with its columns and, for a dataset that a job builds, its lineage **edges**. A raw table has no edges. Each edge is a list of strings:
  - `[outputColumn, input, usage]`: the column `outputColumn` of this dataset (a bare column name) reads `input` (a full name `dataset.column`) in the way `usage` says;
  - `[outputColumn, input, usage, "masking"]`: the same, where the computation also hides the input's values (a hash, a count). Level 4 uses it.
- The **usage** is one of:

  | `usage` | The output... | For example |
  |---------|---------------|-------------|
  | `identity` | is the input's value, copied as it is | `id` is `customer_id` |
  | `transform` | is computed from the input's value in the same row | `amount_eur` is `amount * rate` |
  | `aggregate` | is computed from the input's values over many rows | `total` is the sum of `amount_eur` |
  | `filter` | does not contain the input's value, but the input decides which rows there are | only rows with `status = 'paid'` |

- `addDataset` returns `true`. It returns `false`, and declares nothing, when the name is already declared, the name or a column is not a valid name (1 to 20 characters from `a`-`z`, `0`-`9` and `_`: no capitals, dashes or spaces), a column is listed twice, an edge's output is not one of `columns`, an input is not two valid names joined by one dot (`dataset.column`), a usage is not one of the four, a fourth element is not exactly `"masking"`, masking is given on an `identity` or `filter` edge (a copy hides nothing, and a filter carries no value), an edge has fewer than 3 or more than 4 elements, or two edges join the same output and input.
- An input may name a dataset that is not declared yet: specs arrive from many jobs, in any order.
- `validate()`: the problems of the whole graph as it is now, as a sorted list of issues:
  - `["unknown-dataset", consumer, input]` for each edge whose input's dataset is not declared, where `consumer` is the full name of the edge's output column;
  - `["unknown-column", consumer, input]` for each edge whose input's dataset is declared but has no such column;
  - `["cycle", member1, member2, ...]` for each group of columns that feed each other in a loop: the columns that can each reach every other one by following arrows, members sorted. A column with an edge from itself is a group of one. A cycle means no column of the group can ever be computed first.
- `inputsOf(column)`: the inputs of a column's edges, sorted; `[]` for a column with none.

### Example 1

<!-- case: ex1 -->

The raw tables `crm` and `orders` have no edges. `clean_customers` copies three columns and hashes `email`. A second `crm`, an edge to the undeclared output `b`, and masking on a copy are refused. The graph has no problems, and `email_hash` reads `crm.email`.

### Example 2

<!-- case: ex2 -->

`report` reads `sales.amount` before `sales` is declared, which is an issue until it is. Then `sales` exists but has no `cost`, and `loop.x` and `loop.y` read each other: two more issues, sorted.

## Level 2: Upstream and downstream

- `upstream(column)`: every column the given column depends on, directly or through other columns: its inputs, their inputs, and so on.
- `downstream(column)`: every column that depends on the given one: the columns that read it, the columns that read those, and so on.

Every usage counts as a dependency, `filter` included: when the filter column breaks, so does the output. Inputs that no dataset declares are walked like any other name. The answer is ordered by **distance**, the smallest number of arrows between the two columns, nearest first, and then by name; each column appears once, at its smallest distance. The column itself appears only when it lies on a cycle, at the distance of the shortest way round. The walk must end on a cycle.

### Example 1

<!-- case: ex3 -->

`revenue.total` sums `order_facts.amount_eur` (distance 1), which is computed from `orders.amount` and filtered by `orders.status` (distance 2). `crm.country` is copied into `clean_customers`, then into `order_facts`, then into `revenue`. `orders.status` is only a filter, but `order_facts.amount_eur` and what is built from it still depend on it. `crm.email` is a raw column: nothing is upstream.

### Example 2

<!-- case: ex4 -->

`loop.x` and `loop.y` read each other, so `loop.x` is downstream of itself, at distance 2, the way round through `loop.y`; `loop.z` is at distance 2 too and comes after it by name. Nothing reads `loop.z`.

## Level 3: Impact of a change

Before a source column changes, its owner asks what the change will affect. Three changes are known, and each travels through the graph in its own way:

- `"drop"`: the column disappears. Every job that reads it fails, and everything built from those jobs goes stale: **every** downstream column is affected.
- `"rename"`: the column gets a new name. Only the specs that name it must change: the columns that read it **directly** are affected, and the values further down do not change.
- `"retype"`: the column's type changes, for example from integer to text. The new type travels along `identity` edges, because a copy has the type of what it copies. So the *typed* columns are the changed column and every column reached from it through `identity` edges only. Every column that reads a typed column, through any usage, is affected; the walk stops at a column that computes, aggregates or filters with it, since that column's own type does not change.

Methods:

- `impact(column, change)`: one row `[affected, use]` per affected column, ordered by distance and then name as at level 2. `use` is `"direct"` when the affected column reads the changed column itself (distance 1) and `"derived"` when it is reached through other columns. For a retype, the distance of an affected column is one more than the smallest distance of a typed column it reads, counting the typed columns' distances through `identity` edges.
- `isBreaking(column, change)`: whether the change breaks something. A drop or a rename breaks as soon as anything is affected. A retype breaks when some column reads a typed column through `transform`, `aggregate` or `filter`: an expression written for the old type may fail. A retype that only reaches copies is not breaking: the copies simply take the new type.
- `impactedDatasets(column, change)`: the datasets that hold an affected column, sorted, each once.

Here *direct* and *derived* say how far away a column is. The column-level lineage facet of the OpenLineage specification uses the words for something else: a `DIRECT` input gives the output its value, and an `INDIRECT` one, such as a filter, only affects it. In this problem that difference is the usage.

### Example 1

<!-- case: ex5 -->

Dropping `orders.amount` breaks `order_facts.amount_eur` directly and `revenue.total` through it. Renaming `crm.country` affects only `clean_customers.country`, the one spec that names it. Nothing reads `revenue.total`, so dropping it affects nothing and breaks nothing.

### Example 2

<!-- case: ex6 -->

`a.x` is copied into `b.copy`, then into `c.copy2` and `d.final`: those are typed. `b.calc` computes with `a.x`, `b.flag` filters on it, and `c.sum` aggregates `b.copy`: they are affected, and they make the retype breaking. `c.from_calc` reads `b.calc`, whose type did not change, so it is not affected. Retyping `c.copy2` only reaches the copy `d.final`, which is not breaking.

## Level 4: Sensitive data

Some columns hold personal or secret data. A **label** such as `pii` marks such a column, and the question is where that data ends up.

- `tag(column, label)`: gives a declared column (its dataset is declared and lists it) the label, and returns `true`; `false` for any other column or when the column has that label already.
- A label travels along an edge when the edge carries the input's value into the output: usage `identity`, `transform` or `aggregate`, without masking. A `filter` edge carries no value, and a masking edge hides it, so neither passes a label on. A column carries its own labels and every label that reaches it through any chain of such edges.
- `tagsOf(column)`: the labels a column carries, sorted, each once.
- `publish(dataset)`: marks a declared dataset as published: read outside the platform, by a dashboard, an export or a partner. It returns `true`, or `false` for an unknown dataset or one published already.
- `exposures(label)`: one row `[publishedColumn, source]` for each column of a published dataset and each column `source` that was tagged with `label` and whose label reaches it, sorted. A tagged column of a published dataset exposes itself.

Masking follows the column-level lineage facet of the OpenLineage specification, where it is a flag on a transformation saying that the input value was obfuscated, with hashing a transformation and counting an aggregation as its examples. In the W3C provenance ontology (PROV-O), a derivation is "a transformation of an entity into another"; lineage edges are such derivations between columns.

### Example 1

<!-- case: ex7 -->

`crm.email` and `crm.name` are `pii`; a second `pii` on `crm.email` and a column `crm` does not have are refused. `email_hash` is a masked transform of the email, so it carries no label, while `name` is a copy and carries `pii`. Once `clean_customers` is published, its `name` exposes `crm.name`.

### Example 2

<!-- case: ex8 -->

`orders.customer_id` is `pii` and `orders.amount` is `finance`. In the published `revenue`, `total` sums amounts and carries `finance`, while `buyers` is a masked count and carries nothing. `order_facts.customer_id` carries `pii`, but `order_facts` is not published, so `pii` is not exposed.

## Constraints

- At most 100 datasets, 500 columns and 2000 edges in a graph.
- Labels are 1 to 20 characters from `a`-`z`, `0`-`9`, `_` and `-`; `change` is always `drop`, `rename` or `retype`.
- At most 300 calls per test.

## Follow-ups

- A join key decides which rows meet, like a filter, and a sort key decides their order. How would you add `join` and `sort` usages, and should either carry a label?
- A masked count still leaks something when a group has one member. What rule would you add for aggregates over small groups?
- Lineage specs written by hand drift from the code they describe. Where else could the edges come from, and how would you notice an edge that is missing?
- A retype from a narrow integer to a wider one breaks nothing that only reads. How would you describe types precisely enough to tell a widening from a narrowing?

## Hints

### Hint 1

Give every column one name, `dataset.column`, and keep two maps of lists: from a column to the edges that leave it (its consumers) and from a column to the edges that enter it (its inputs). An edge records its input, its output, its usage and whether it masks. `addDataset` checks every edge first and only then adds them all, so a refused dataset adds nothing.

### Hint 2

Unknown inputs are found edge by edge at validation time, not when a dataset is added: by then the dataset may exist. Split each input at the dot and look the dataset and the column up.

### Hint 3

For upstream and downstream, a breadth-first search gives distances in increasing order for free. Start from the column with distance 0 but do not count it as visited: it appears in the answer only if an arrow leads back to it.

### Hint 4

Columns that feed each other form strongly connected groups. Compute them with two depth-first passes (Kosaraju's algorithm) or with Tarjan's single pass, using explicit stacks; a group of one is a cycle only when its column has an edge from itself.

### Hint 5

The three changes are the same breadth-first search with a different rule for which edges it may continue along: every edge for a drop, none after the first step for a rename, and for a retype, first a search along `identity` edges to find the typed columns, then one step along any edge from each of them.

### Hint 6

Labels need the same search with yet another rule: continue only along edges that carry a value and do not mask. For `tagsOf`, search backwards and collect the labels of every column you meet; for `exposures`, search forwards from each tagged column and keep the columns of published datasets.
