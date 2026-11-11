# Triple Store

## Statement

Build `TripleStore`, a small in-memory database for *facts*. A fact is written as three words: `alice knows bob`, `bob livesIn paris`, `paris capitalOf france`. Such a database can answer "who does Alice know?", "who lives in a city that is a capital?" and "what was true last March, and who told us?". The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a triple?** A *triple* is one fact with three parts: a **subject** (what the fact is about), a **predicate** (the kind of relation) and an **object** (what the subject is related to). In `alice knows bob`, `alice` is the subject, `knows` the predicate and `bob` the object. Each part is a *term*: just a name, here a string of text. A set of triples is a *graph*: draw each term as a dot and each triple as an arrow from the subject to the object, labelled with the predicate, and the facts become a map of connections. Several facts can mention the same term, which is how facts connect: `alice knows bob` and `bob livesIn paris` meet at `bob`.

**Where it comes from.** RDF, the W3C's Resource Description Framework, is built on this idea: an RDF graph is a *set* of triples (RDF 1.1 Concepts and Abstract Syntax), so a triple is either in the graph or not, and it cannot be in it twice. SPARQL is its query language. Real RDF is stricter about what may be a subject, predicate or object (an RDF predicate is always an IRI, and a literal cannot be a subject); this problem allows any term anywhere, which RDF 1.1 calls *generalized* triples. Terms here are plain strings, with none of RDF's IRIs, literals or blank nodes.

**How it is stored.** The store must stay fast with many facts. Looking at every triple to answer one question is a *scan*, and its cost grows with the size of the store. An *index* is a lookup table kept next to the data: one that lists the triples of each subject finds "everything about `alice`" without a scan, and one per predicate and per object do the same for "everyone who `knows`" and "everything about `paris`". Level 1 asks you to design these tables.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `TripleStore()`: creates an empty store.
- A **term** is a non-empty string of printable ASCII characters (codes 33 to 126, so no space), at most 30 characters, compared exactly as given: `Alice` and `alice` are different terms. A term never starts with `?` and never ends with `+`: those two characters are how patterns tell variables and paths apart from terms.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the store return a `bool`. Questions return a list of triples, a list of rows or an `int`. A triple is a list of three terms, `[subject, predicate, object]`. Where a method says "sorted", texts are compared by the numeric value of their characters, so that `B` comes before `a`, and `10` before `9`; triples are sorted by subject, then predicate, then object, and rows by their first term, then their second, and so on.

## Level 1: Facts and patterns

- `add(subject, predicate, obj)`: adds a triple. It returns `true` when the triple was not in the store, and `false` when it was already there and nothing changed. (The object is called `obj` because some languages reserve the word `object`.)
- `remove(subject, predicate, obj)`: removes a triple. It returns `true` when the triple was in the store and `false` when it was not.
- `size()`: the number of triples in the store.
- `match(subject, predicate, obj)`: the triples that fit a **pattern**, sorted. Each of the three positions of a pattern is either a term, which a triple must have in that position, or the **wildcard** `"?"` (just a question mark), which any term fits. `match("alice", "?", "?")` is everything about `alice`, `match("?", "knows", "?")` is every `knows` fact, and `match("?", "?", "?")` is the whole store. A pattern with three terms returns the triple when it is in the store and `[]` otherwise. At this level a pattern uses only terms and `"?"`.

**Indexes.** A pattern has up to three bound positions, and so there are eight shapes: which of subject, predicate and object are given. A good store answers every shape from a lookup table instead of a scan. One table per position (subject to triples, predicate to triples, object to triples) answers the three shapes with one bound position, and one more table per *pair* of positions answers the shapes with two. A store can instead keep three tables in the orders subject-predicate-object, predicate-object-subject and object-subject-predicate (an "SPO, POS and OSP" layout): every shape is then a prefix of one of the orders. Either way, the work for a match is the size of the answer, plus sorting it, and not the size of the store. The tests do not check how you find the triples; the larger levels have inputs where a scan is too slow.

### Example 1

<!-- case: ex1 -->

The second `add` of `alice knows bob` returns `false` and changes nothing: `size` counts three triples, not four. `match("alice", "?", "?")` lists everything about `alice`, and the triples come back sorted. After `alice likes tea` is removed, removing it again returns `false`, and a match for it is empty.

### Example 2

<!-- case: ex2 -->

The triples were added in no particular order and come back sorted. `match("?", "?", "bob")` is a lookup by object only, `match("bob", "?", "paris")` binds the subject and the object, and a pattern of three terms is a membership test. The last two patterns match nothing.

## Level 2: Joined queries

A single pattern asks about one fact. Most questions need several facts together: "who does Alice know, and where do those people live?" is two patterns joined by a person. A **query** is a list of patterns that may share **variables**.

- A **variable** is `?` followed by at least one letter, digit or underscore: `?x`, `?friend`, `?y2`. A pattern position is now a term, a variable, or the bare wildcard `?`.
- A **solution** of the query gives each variable a term, so that every pattern, with its variables replaced by their terms, is a triple that is in the store. A variable has one term in a solution, wherever it appears: in the subject of one pattern and the object of another, in the predicate position, and twice in one pattern (`?x knows ?x` asks for someone who knows themselves). A pattern with no variable is a condition: the answer is empty when its triple is not in the store. The bare wildcard `?` fits any term and does not bind anything: two `?` in a query are unrelated.
- `query(patterns, columns)`: `patterns` is a non-empty list of patterns, each a list of three strings, and `columns` is a non-empty list of variables that all appear in `patterns`. The answer has one **row** for each distinct combination of terms that the variables of `columns` take in some solution, in the order of `columns`. The rows are sorted, and no row is repeated, even when several solutions give the same row.

This is a *basic graph pattern* of the SPARQL query language, and a SPARQL `SELECT DISTINCT` of the same variables. SPARQL itself returns its solutions without a promised order and may repeat them; here the order and the distinctness are fixed so that every answer can be checked.

**Join order.** The answer does not depend on the order of the patterns, but the work does. Matching `?a knows ?b` first lists every `knows` fact before the next pattern can use `?b`. Matching the most selective pattern first, and the patterns that now have a variable bound after it, works through far fewer candidates.

### Example 1

<!-- case: ex3 -->

`?a knows ?b` and `?b knows ?c` share `?b`, the object of one and the subject of the next: Alice knows Bob, and Bob knows Carol and Dave. Selecting only `?b` gives Bob once, although two solutions have him. In the third query the rows follow `columns`, `?y` before `?x`. A query with no solution gives `[]`.

### Example 2

<!-- case: ex4 -->

`?x knows ?x` finds the two people who know themselves. A variable can also stand for a predicate: `?x ?p ?x` lists, for each term that is both subject and object of one fact, the predicate. In the third query, Ann is the only person who knows Ben and also knows herself.

## Level 3: Paths through the graph

Some questions follow a relation any number of times: "who is above Dana in the chain of command?", "which pages can I reach from this one?". A **path** pattern names a predicate followed by `+`: `reportsTo+` is one or more `reportsTo` arrows in a row, followed in the direction of the arrows, from subject to object.

- In a query, the predicate position of a pattern may be a term followed by `+` (never a variable). The pattern `x reportsTo+ y` fits when there is a chain `x reportsTo t1`, `t1 reportsTo t2`, ..., `tk reportsTo y` of at least one triple. `x` and `y` can each be a term, a variable or the bare `?`, and a path takes part in a join like any other pattern: its variables are shared with the other patterns.
- Only the chosen predicate is followed. The chain follows the arrows forward, never backwards.
- **A cycle must not make the query loop.** If `a next b`, `b next c` and `c next a`, a walk that keeps following arrows never stops. A path pattern fits for a pair of terms at most once: it is about *whether* `y` is reachable from `x`, and not about how many ways lead there.
- **The start node.** The chain has at least one arrow, so `x reportsTo+ x` fits only when the arrows lead from `x` back to itself: when `x` is on a cycle, which includes a triple whose subject and object are both `x`. A node that is not on a cycle is not reached from itself. (`p*`, "zero or more", would include the start; it is not part of this problem.)

This matches the `+` operator of SPARQL 1.1 property paths, a one-or-more path ("OneOrMorePath"), whose arbitrary-length matching is defined over *distinct* nodes so that cycles never make it infinite and never repeat a node.

`match` does not understand paths. `query` is the only method that takes them at this level.

### Example 1

<!-- case: ex5 -->

`dana reportsTo erin`, `erin reportsTo fay`, `fay reportsTo gus`, and `hal reportsTo fay`. The path from Dana reaches `erin`, `fay` and `gus`, and the path *to* `gus` starts from everyone below. With both ends open, the answer lists every pair joined by a chain, each once. `gus` reports to nobody, so the path from `gus` is empty. The fourth query joins a path with a pattern: it asks for people above `hal` who like something, and nobody above `hal` does.

### Example 2

<!-- case: ex6 -->

`a`, `b` and `c` form a cycle. The path from `a` reaches `b`, `c` and, going once round, `a` itself. `d` leads into the cycle without being on it: it reaches `a`, `b` and `c`, but not itself. `e` has an arrow to itself, which is a cycle of one. `?x next+ ?x` lists exactly the nodes on a cycle: `a`, `b`, `c` and `e`. The last query joins the path with `a tag ?t`.

## Level 4: Sources and time

A real fact has a history: someone told you, at some moment, and later it may stop being true. This level adds a **source** and a **time** to every triple and lets you ask what the store knew at any moment, and who said so. The time is a number of your choice, such as a count of milliseconds; the store never reads a clock, it uses the times it is given, which are integers from `0` to `10^15`.

- A **source** is any text of printable ASCII characters (codes 32 to 126), at most 30 characters. The empty source `""` means that no source is given.
- `record(subject, predicate, obj, source, time)`: says that `source` states the triple at `time`. If the triple is not in the store, it is added from `time` and the call returns `true`. If it is already in the store, nothing is added: `source` joins the sources of the triple and the call returns `false` (a source already among them changes nothing).
- `retract(subject, predicate, obj, time)`: removes the triple at `time`. It returns `true` when the triple was in the store and `false` when it was not. **Removing keeps the history.**
- `queryAsOf(patterns, columns, time)`: the answer `query` would have given at `time`: the store as it was then. Patterns contain no paths.
- `sourcesAsOf(patterns, columns, time)`: the sources behind each row of `queryAsOf` with the same arguments, in the same order: one list per row, sorted, with each source once and the empty source left out. The sources behind a row are the sources of every triple that some solution giving the row used for its patterns, as of `time`.

**The history of a triple** is a list of **spans**. A span starts when the triple is added (by `record`, or `add`) and ends when it is retracted. The triple is in the store at time `T` when `T` falls in a span, from its start up to but not including its end: *start <= T < end*. A triple that has not been retracted is in the store from its start on. Recording a triple again after it was retracted starts a new span, with only the sources of that record. The sources of a span, as of time `T`, are those that recorded the triple in this span at a time up to and including `T`.

**The clock.** Times given to `record` and `retract` never go down from one call to the next, equal times are allowed, and a call happens after the calls before it, even at the same time. The earlier methods keep working on the current state, and they use the time of the latest `record` or `retract` (`0` before there is one): `add(s, p, o)` is `record(s, p, o, "", now)` and `remove(s, p, o)` is `retract(s, p, o, now)`. `size`, `match` and `query` answer for the store after all the calls so far.

A span that starts and ends at the same time contains no moment and is never seen.

This is *transaction time*: when the store learned or dropped a fact, and not when the fact was true in the world. Storing both is called a bitemporal design. RDF attaches sources to triples with named graphs (RDF 1.1 Concepts, section 4: a dataset holds graphs that have names), and this problem stores the source with the triple.

### Example 1

<!-- case: ex7 -->

`alice knows bob` is recorded by `crm` at time 10, and again by `import` at 20: the second call returns `false` and adds a source. At time 5 the triple is not yet there. At 10 it is, with the source `crm`; at 25, with `crm` and `import`. It is retracted at 40, so it is there at 39 and not at 40, and `match` no longer finds it. Recording it again at 50 starts a new span: its only source is `web`, and the answers about time 25 do not change.

### Example 2

<!-- case: ex8 -->

The sources of a row are those of every triple behind it. At time 3, `paris` rests on the triple `alice knows bob` from `s1` and `bob livesIn paris` from `s2`; at 5, `s3` has recorded the second one too. At time 8 there are two rows: `paris` still has `s1`, `s2` and `s3`, and `rome` has `s1` and `s4`. After `bob livesIn paris` is retracted at 9, only `rome` is left, and a query as of 100 shows only the triples that are still there.

## Constraints

- At most 2 * 10^5 calls per test, and at most 10^5 triples in the store at once.
- A query has at most 8 patterns and at most 8 variables in `columns`; a pattern list has at least one pattern.
- A path query with both ends open is asked only on stores where the answer has at most 10^5 rows.
- The answer to one call has at most 10^5 entries, and a path can be 10^5 hops long, so walk with a queue or a stack of your own instead of recursing.

## Follow-ups

- Real stores keep three sorted indexes (SPO, POS, OSP) instead of six hash tables, and answer every pattern as a range scan. What would you gain, and what would a sorted layout cost on `add`?
- `queryAsOf` filters by span at query time. How would you keep a separate "live" index so that queries about now never touch the dead triples, and when would you compact the history?
- SPARQL also has `p*` (zero or more hops), `^p` (the reverse of `p`), `p/q` (a sequence) and `p|q` (either). Which of them need nothing but a different starting set for the walk?
- A join can pick its order from the sizes of the candidate lists, but those sizes ignore how the variables bound so far narrow them. How would you estimate a better order?
- Here a triple's source list belongs to the triple. What changes when two sources disagree, for example one retracts what another asserted?

## Hints

### Hint 1

A triple is a row with three fields, and a store is a set of rows. Think about the question "who does Alice know?": you want to go from the word `alice` to all rows that have it as subject, without reading the other rows. A dictionary does exactly this: its keys are subjects and its values are lists of triples. A second dictionary for predicates and a third for objects cover the other two single-position questions.

### Hint 2

Give every triple a number when it first appears, and keep lists of numbers in the dictionaries. Then a triple lives once, in one array, and the dictionaries only point at it. For two bound positions, use a dictionary whose key is the pair. For three, a dictionary from the whole triple to its number is also how `add` finds out that a triple is already there.

### Hint 3

Do not delete a triple when it is removed. Mark it as removed (at level 4, close its span) and keep its number in the lists. Adding it again reuses the number. Queries skip the triples that are not present. This costs a little space and makes the history at level 4 free.

### Hint 4

For a query, keep a dictionary from variable to term, the bindings so far. Take one pattern, replace the variables that are bound, look up the candidates with the index that fits the bound positions, and for each candidate try to bind the variables that are still free: a term must equal the one already bound. Then do the same with the remaining patterns, and undo the bindings when you go back to try the next candidate. At the end of the list, record the row.

### Hint 5

Choose the next pattern by looking at how many candidates each remaining pattern has under the current bindings, and take the smallest. A pattern whose three positions are all bound costs at most one lookup. Collect rows in a set and sort at the end.

### Hint 6

A path is a graph walk. Keep a queue and a set of nodes already reached. Start with the queue holding the start node and the set empty. Take a node, look at the targets of the arrows `node p target`, and for each target not yet in the set, add it to the set and to the queue. The set, and not the start node, is the answer. The start node gets into the set only if an arrow leads back to it. Because a node is added once, a cycle ends the walk.

### Hint 7

For a path whose end is known, walk from that end: forward from a known start, backward from a known end (using the index on predicate and object). When neither end is known, use as starts every subject of an arrow of that predicate. When both are known, walk from one and check the other.

### Hint 8

At level 4 each triple keeps a list of spans, `[start, end, sources]`, with `end` set to a huge number while the span is open. The triple is present at `T` when some span has `start <= T < end`, and since the spans are in time order you can look at them from the last one. A source is stored with the time it recorded the triple, and `sourcesAsOf` keeps only those at or before `T`. To get the sources of a row, remember the numbers of the triples each solution used.
