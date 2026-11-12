# Lineage Graph: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| adjacency-walks | optimal | O(V + E + A log A) per validation or walk, V columns, E edges, A answers; O(S (V + E)) per exposure report of S labelled sources | O(V + E) | default answer; one breadth-first search with a rule for which edges it follows serves every query |

Here `V` is the number of column names in the graph, declared or only referenced, `E` the number of edges, `A` the size of an answer and `S` the number of columns tagged with the label asked for.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Specs, unknown inputs and cycles | the declared datasets with their columns, the list of edges, and two maps from a column to its outgoing and its incoming edges |
| 2 | Ordered walks | nothing new: a breadth-first search over one of the two maps |
| 3 | Changes | nothing new: the same search, restricted by the usage of the edges it may follow |
| 4 | Labels | the labels given to each column and the set of published datasets |

The early choice that carries every level is to write the walk once, with two parameters: which map to follow (consumers or inputs) and which edges it may cross. Upstream and downstream follow every edge; a rename follows one step; a retype follows identity edges and then one more step; labels follow the edges that carry an unmasked value. A first version with separate walks for each question repeats the same subtle rule (the start is in the answer only on a cycle) four times.

## Approach: adjacency-walks (Forward and backward adjacency with breadth-first walks and cycle groups)

### Intuition

A lineage graph is a directed graph whose nodes are columns and whose edges carry a usage. Every question is reachability with a rule: "which columns can be reached from here, following only edges of this kind, and how far are they?". Breadth-first search answers it and gives the shortest distance of each column as it goes, which is exactly the order the answers need. Cycles are a property of the whole graph rather than of one walk, so they come from strongly connected components.

### Algorithm

1. `addDataset` checks the name, the columns and every edge, and only then records the dataset and appends each edge to the outgoing list of its input and the incoming list of its output.
2. `validate` splits each edge's input at the dot and reports an unknown dataset or column. For cycles it runs Kosaraju's algorithm: a depth-first pass over the outgoing edges that records the order in which columns finish, then a pass over the incoming edges in reverse finishing order, where each search collects one strongly connected group. Groups with two or more columns, or one column with an edge from itself, are cycles. The issues are sorted.
3. A walk starts a queue at the column with distance 0, without marking it visited, and for each column taken from the queue follows its allowed edges, giving each newly reached column the current distance plus one. The answer is sorted by distance and then name.
4. `impact` for a drop walks every outgoing edge; for a rename takes the direct consumers; for a retype first walks identity edges to find the typed columns and their distances, then takes every consumer of a typed column at one more than that distance, keeping the smallest. `isBreaking` for a retype looks for a non-identity edge leaving a typed column.
5. `tagsOf` walks incoming edges that carry a value and do not mask, and unions the labels of the column and of every column it meets. `exposures` walks outgoing edges of the same kind from each column tagged with the label, the column included, and keeps the columns of published datasets.

### Correctness

Breadth-first search visits columns in order of their distance from the start, so the first time it reaches a column is along a shortest path, and the distance it records is the smallest. It marks a column when it reaches it, so each column is recorded once and the search ends on a cycle. The start is never marked at distance 0, so it is recorded only if an edge leads back to it, which is the definition of lying on a cycle. Restricting the edges the search may cross restricts the paths it considers, which is how each change and each label gets its own reach.

For a retype, the typed columns are exactly those reachable through identity edges, because a copy has the type of what it copies and nothing else passes the type on. A column is affected exactly when it reads a typed column, and its distance is the shortest way to it: a shortest typed path followed by one edge.

Kosaraju's algorithm is correct because the component of the column that finishes last in the first pass is a source component of the graph of components; in the reversed graph it is a sink, so a search from it reaches exactly its own component, and removing it leaves the same property for the rest.

### Complexity

- Time: O(V + E + A log A) per validation or walk, V columns, E edges, A answers; O(S (V + E)) per exposure report of S labelled sources — each search visits every column and edge at most once and the answer is then sorted; Kosaraju's two passes are linear; an exposure report runs one search per tagged source.
- Space: O(V + E) — the two adjacency maps hold every edge twice, and a search keeps a queue and a distance map over the columns.

### Trade-offs

- Computing on demand keeps adding a dataset cheap and answers always current. A platform that asks the same question often would precompute, for example, the labels of every column after each change, at the cost of updating them when a spec changes.
- Breadth-first search gives distances; a depth-first search finds the same columns but in an order that depends on the edges, which is why the statement fixes the order by distance.
- Grouping cycles by strongly connected components reports each loop once, however many columns and edges it has. Listing every elementary cycle instead can take exponential time.
- The retype rule is deliberately coarse: it does not know whether an expression accepts the new type. A real tool would record types per column and tell widening from narrowing.

### Pitfalls and edge cases

- `addDataset` is all or nothing: one bad edge refuses the whole dataset. Masking is allowed only on `transform` and `aggregate`, and usages are compared exactly.
- Inputs are checked when `validate` runs, not when a dataset is added: a dataset declared later clears the issue. A missing dataset and a missing column have different codes, and every consumer of an unknown input is its own issue.
- A cycle is reported once per group, with its members sorted; a column that reads itself is a cycle of one.
- Upstream follows inputs and downstream follows consumers. A filter input is a dependency. Undeclared inputs are still walked.
- Order by distance first. A column reached along a long and a short path appears once, at the short one.
- The column itself appears in its own walk only on a cycle.
- A rename affects only direct consumers; a retype stops at the first column that does not copy it; a drop reaches everything downstream.
- Direct and derived are about distance, not about the usage of the edge.
- A retype that reaches only copies is not breaking; one that a filter reads is.
- Labels: masked edges and filters stop them, aggregates without masking pass them on, and they travel any number of hops. A column keeps its own labels. A tagged column of a published dataset exposes itself, and a published column with two tagged sources gives two rows.

### Language notes

- Python's `deque`, TypeScript's array with a moving head index, Java's `ArrayDeque`, Kotlin's `ArrayDeque`, Go's slice with a head index and Rust's `VecDeque` serve as the queue.
- The first pass of Kosaraju's algorithm keeps an explicit stack of columns, each with its position in its edge list (an iterator in Python, an index elsewhere), so a long chain of columns cannot overflow the call stack.
- Splitting `dataset.column`: Python's `split`, TypeScript's `split`, Java's `indexOf` with `substring`, Kotlin's `split`, Go's `strings.Cut` and Rust's `split_once`. An input is well formed when it has exactly one dot with text on both sides.
- Labels per column are a set in every language; the answers are sorted at the end.

## Further reading

- [OpenLineage, Column Level Lineage Dataset Facet](https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet): each output field lists its input fields with transformations of type `DIRECT` (the output value is derived from the input) or `INDIRECT` (the input affects the output without being its value), subtypes `IDENTITY`, `TRANSFORMATION`, `AGGREGATION`, `FILTER` and others, and a `masking` flag for obfuscated inputs, with hashing and counting as examples.
- T. Lebo, S. Sahoo and D. McGuinness (editors), [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/), W3C Recommendation, 30 April 2013: entities, and derivation as the transformation of one entity into another.
- R. Tarjan, ["Depth-First Search and Linear Graph Algorithms"](https://doi.org/10.1137/0201010), SIAM Journal on Computing 1(2), 1972, pages 146 to 160: strongly connected components in time linear in the vertices and edges.
