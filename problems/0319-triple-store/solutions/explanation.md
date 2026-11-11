# Triple Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| six-indexes | optimal | O(1) per add, remove or record; O(k log k) per match of k triples; per query, the candidates examined plus the nodes walked | O(n) with six index entries per triple | default answer; one set of indexes and one list of spans serve all four levels |

Here `n` is the number of triples ever recorded and `k` the number of triples in an answer.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Number the triples and index them | `triples` (an array), `exact` (a whole triple to its number) and six indexes by subject, predicate, object and the three pairs, each a list of numbers |
| 2 | Joins by backtracking | nothing new: a query keeps a map of bindings and chooses the next pattern by the length of its candidate list |
| 3 | Paths | nothing new: a path is a breadth-first walk over the pair indexes `(subject, predicate)` and `(predicate, object)` |
| 4 | Sources and time | a list of spans for every triple; the indexes keep the numbers of removed triples, and every lookup checks that the triple is present at the time asked |

The early choice that keeps level 4 cheap is to never delete from the indexes. A first version that removes a triple from its lists answers levels 1 to 3 correctly, and then loses the history it needs at level 4: the removal has to become "close the span", every lookup has to check presence, and `add` after `remove` has to reuse the old number. Here a triple gets a number the first time it is added, and removing it only changes its state.

## Approach: six-indexes (Six hash indexes over numbered triples with spans)

### Intuition

A pattern has up to three bound positions, and what is bound decides which list to start from. An index is a map from the bound terms to the numbers of the triples that have them. With the maps for subject, predicate, object and each pair, there is a map for every shape of pattern, so a pattern always starts from the shortest list that is exact for it, and a fully bound pattern is one map lookup. A join is then a nested loop over those short lists, with the most selective pattern outermost. A path is a walk on the same maps. Time is a list of spans on each triple, and "as of" is a check against the spans instead of a copy of the store.

### Algorithm

1. Level 1: the first time a triple is seen, give it the next number, store it, and append the number to the six index lists and to `exact`. `add` and `remove` change the triple's state. `match` turns each bound position into a key, picks the index for that shape, keeps the triples that are present, and sorts them by subject, predicate and object.
2. Level 2: a query keeps a map from variable to term. While patterns remain, compute for each the number of candidates under the current bindings (replace a bound variable by its term, look up the index) and take the smallest. For each candidate triple that is present, try to bind the pattern's variables: a term must equal the bound value, a variable that is bound must equal it, and a variable that appears twice must get the same term twice. Recurse on the other patterns with the new bindings, then undo them. When no pattern remains, record the row of the selected variables. Collect the rows in a set and sort them.
3. Level 3: a path pattern takes its subject or object from the bindings. With a known start, walk forward with a queue and a visited set, following the `(subject, predicate)` index; with only a known end, walk backward over `(predicate, object)`; with neither, walk forward from every subject of the predicate. The visited set starts empty and gets a node when an arrow reaches it, so the start is in it exactly when a cycle leads back.
4. Level 4: `record` opens a span `[time, open)` when the triple is absent and otherwise adds the source with its time to the open span. `retract` sets the end of the open span. A triple is present at `T` when some span has `start <= T < end`. `sourcesAsOf` runs the same search and keeps, for each solution, the numbers of the triples it used; the sources of a row are the sources of those triples' spans at `T` that were recorded at or before `T`.

### Correctness

Indexes: every triple that ever existed is in its six lists exactly once, and the lists are never shortened. A pattern's bound positions select the list that holds exactly the triples with those terms, so filtering by presence leaves exactly the triples that match. A pattern with three bound terms goes through `exact` and is a membership test.

Join: the search is the definition of a solution. A solution gives each variable one term such that every pattern, instantiated, is a present triple. The loop chooses the patterns in some order, and at each step it extends the bindings by every present triple that is consistent with them, so every solution is built exactly once for each order of choice, and nothing else is built. The order of choice changes the work, not the set of solutions.

Path: let `R` be the visited set when the queue is empty. Each node of `R` was added because an arrow leads to it from the start or from a node of `R`, so it is reachable by one or more arrows. Conversely, if `y` is reachable by a chain of arrows from the start, the first node of the chain is added when the start is dequeued, and each following node is added when its predecessor is dequeued, unless it is in `R` already. So `R` is exactly the set of nodes at the end of a chain of one or more arrows, and each node is dequeued once, which makes the walk finish on a cycle.

Time: for a triple, the spans are in time order and do not overlap, because a span is opened only when the last one is closed, and times never go down. So the last span with `start <= T` is the only one that can contain `T`. A span with `end == start` contains no moment. A retract and a record at the same time `T` close one span at `T` and open the next at `T`, so `T` belongs to the new span.

### Complexity

- Time: O(1) per add, remove or record; O(k log k) per match of k triples; per query, the candidates examined plus the nodes walked — an add, remove or record is a few hash lookups and a push; a match reads the list of its shape and sorts the k triples it returns; a join examines the candidate lists of the patterns it expands, and a path visits each node and each arrow of its predicate once.
- Space: O(n) with six index entries per triple — each triple is stored once and appears in six lists, in `exact` and in its spans, which grow by one entry for each record or retract.

### Trade-offs

- Six hash maps spend memory to make every shape a direct lookup. Real stores keep three sorted copies (SPO, POS, OSP): every shape is then a prefix of one order and a range scan, answers come out sorted, and a merge join is possible, at the cost of O(log n) per insert and no direct lookup by pair.
- Keeping removed triples in the indexes makes queries about now scan dead entries. A separate index of live triples, or a compaction that drops spans older than a horizon, trades history for speed.
- Choosing the next pattern by candidate count is a heuristic: the number of candidates ignores how many of them survive the bindings that come later. Cost-based planners keep statistics about how selective each predicate is.
- A path with both ends open is a walk from every start: O(V(V + E)) for V nodes, and the answer can be quadratic. The tests keep such queries to small graphs; a real engine would materialize the closure or refuse the query.

### Pitfalls and edge cases

- A store is a set: adding a triple twice is `false` the second time, and `size` counts it once. A triple that is added again after a removal is new.
- `match` and `query` return sorted answers, and the sort is by character value, so `B` precedes `a` and `10` precedes `9`.
- A variable that appears twice in one pattern is a condition, not two free positions. A bare `?` is not a variable: two of them in a query are unrelated.
- A pattern without variables must still be true for the query to have an answer.
- The rows are distinct: two solutions that differ only in a variable that is not selected give one row. Joining on a variable that is not selected is the usual way to get duplicates.
- A path with the same variable at both ends lists the nodes on a cycle, including a node with an arrow to itself. A start that is not on a cycle is not reached from itself.
- A path follows arrows forward only, and only the named predicate.
- Presence is `start <= T < end`: a triple is there at the moment it is recorded and gone at the moment it is retracted. A triple recorded and retracted at the same time is never seen.
- Sources: the empty source is never listed; a source that records the same triple twice is listed once; a new span after a retraction starts with an empty list; and a source that recorded after `T` is not behind an answer as of `T`.
- `add` and `remove` use the time of the latest `record` or `retract`, so they must move the clock too. Using time 0 hides a triple from every earlier question.
- Recursion depth: the hidden case with a chain of 1,100 hops fails a path walk that recurses once per hop in Python, and the generated case, with a chain of 20,000, fails it in every language.

### Language notes

- Keys of the pair indexes join the two terms with a character that cannot be in a term (the NUL character). Terms have no spaces, so a space would also work; a tuple key, as Python uses, avoids the question.
- Sorting: Python compares tuples and strings by code point, TypeScript's `<` compares UTF-16 units, Java and Kotlin `compareTo` do the same, and Go and Rust compare bytes. All of them agree on printable ASCII, and the statement fixes ASCII.
- `object` is a keyword in Kotlin, and `match` is one in Rust (written `r#match`), which is why the parameter is `obj` and why the Rust method has a raw identifier. Go exports `Match`, `Record` and the rest.
- Times are `long` in Java and Kotlin, `int64` in Go and `i64` in Rust. The largest time is `10^15`, and the sentinel for an open span, `2^53 - 1`, is the largest integer a TypeScript number holds exactly.
- Rust returns the candidates as an enum that borrows the index lists (all, a list, one number) instead of copying them, because a join asks for the size of every remaining pattern at every step. The other languages return a reference to the same list.

## Further reading

- [RDF 1.1 Concepts and Abstract Syntax, W3C Recommendation, 2014](https://www.w3.org/TR/rdf11-concepts/): triples and their terms (section 3), graphs as sets, generalized triples (section 7), datasets and named graphs (section 4).
- [SPARQL 1.1 Query Language, W3C Recommendation, 2013](https://www.w3.org/TR/sparql11-query/): basic graph patterns, property paths (section 9, `elt+` is the one-or-more path) and the evaluation of arbitrary-length paths over distinct nodes (section 18.4).
- C. Weiss, P. Karras and A. Bernstein, "Hexastore: sextuple indexing for semantic web data management", Proceedings of the VLDB Endowment, 2008: the six-index layout.
- T. Neumann and G. Weikum, "The RDF-3X engine for scalable management of RDF data", The VLDB Journal, 2010: sorted permutation indexes and join ordering for triples.
- R. T. Snodgrass, "Developing Time-Oriented Database Applications in SQL", Morgan Kaufmann, 1999: transaction time and valid time.
