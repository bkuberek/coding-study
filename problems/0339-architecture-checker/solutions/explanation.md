# Architecture Checker: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-walks | optimal | O(I log I) after a change, to resolve and sort the I imports; then O(V log V + I R) per walk or cycle search, with R the ignores and exceptions of the contract checked | O(V + I) | default answer; one resolved graph with sorted lists serves all four levels |

Here `V` is the number of declared modules, `I` the number of imports, and `R` the number of ignores and live exceptions of the contract being checked (0 outside contracts).

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Resolve imports, walk the graph | the imports as written per module, and a cached graph: for each module, the sorted list of modules its imports resolve to, rebuilt on the first question after `addModule` |
| 2 | Components and the shortest cycle | nothing new: groups are computed per call, components with two depth-first passes, and `cycleChain` is a walk from one module |
| 3 | Contracts | a map from contract name to its list of `(from, to)` pairs; `check` walks once per `from` name |
| 4 | Ignores, exceptions, modes, baseline | per contract a mode, a set of ignores and a map of exceptions; one current version; one baseline set |

The early choice that keeps the later levels small is to keep the imports *as written* and resolve them lazily. A first version that resolves each import when its module is declared answers the examples where modules come in order, and then fails as soon as an import names a module declared later, or a longer module appears that should now win. Keeping the text and caching the resolved graph until the next `addModule` costs one rebuild per change. The other choice is to sort each module's targets once: every walk then visits neighbours in name order, which is what makes the first chain found the smallest one, at every level.

## Approach: ordered-walks (Resolved import lists with breadth-first walks in name order and two-pass components)

### Intuition

Everything in this problem is a question about paths in one directed graph. Breadth-first search from a set of starts reaches modules in order of distance, so it answers "nearest first" and "shortest chain" directly. If the starts are taken in sorted order and each module's imports are visited in sorted order, the queue holds modules in the order of their chains compared element by element, so the first time a module is reached is along its smallest shortest chain: remembering where each module was first reached from is enough to rebuild that chain. Cycles are a different kind of question, about mutual reachability, and strongly connected components answer it for every module at once.

### Algorithm

1. Level 1: `addModule` stores the imports as written and drops the cached graph. The graph is rebuilt on demand: for each import, try the whole text, then cut off the last part at a dot, until a declared module is found; leave out a target that is the module itself, and sort each module's distinct targets. `members(name)` lists the declared modules equal to `name` or starting with `name` and a dot, sorted. `dependencies` collects the targets of the members that are not members. `transitiveDependencies` walks breadth-first from all members at once, computes each module's distance from the module it was reached from, and sorts the reached non-members by distance, then name.
2. Level 2: `cycles(depth)` maps each module to its group (its first `depth` parts, or itself for depth 0), builds the graph of groups without arrows from a group to itself, and finds its strongly connected components: a first depth-first pass records the order in which nodes finish, and a second pass over the reversed graph, taking roots in reverse finishing order, collects one component per root. Components of one member are dropped; members and components are sorted. `cycleChain(name)` walks breadth-first from `name`; the first module taken from the queue that imports `name` ends the cycle, and the chain back to `name` plus `name` is the answer.
3. Level 3: each contract becomes a list of `(from, to)` pairs: every lower layer with every higher layer, the one forbidden pair, or every ordered pair of independent names. `check` takes the contracts by name, and for each distinct `from` name walks once from its sorted members; for each `to` name of that `from`, the first module in discovery order that `to` covers ends the chain.
4. Level 4: the walk skips an import when an ignore of the contract, or an exception that is live at the current version, covers its importer and its imported module. In direct mode the chain of a pair is the first import, over the sorted members and their sorted targets, from a member of `from` to a module of `to`. Versions become lists of integers without trailing zeros, compared element by element. `ratchet` compares the broken pairs with the baseline set, lists the new ones with their chains, then the fixed entries, and removes the fixed entries from the set.

### Correctness

Resolution: the loop tries the import, then each shorter start that ends at a dot, from longest to shortest, so the first declared name it meets is the longest one that equals the import or starts it at a dot. Rebuilding on every change makes the answer independent of declaration order.

Smallest shortest chains: let the queue start with the starts in sorted order. Claim: the modules at each distance leave the queue in the order of their chains, where each module's chain is the chain through the module it was first reached from. At distance 0 the chains are single modules, in sorted order. Suppose the claim holds at distance `d`. A module `v` at distance `d + 1` is first reached while the queue processes the earliest module `u` at distance `d` that imports it, and modules are added in the order (position of `u`, name of `v`), which is the order of the chains `chain(u) + [v]`. Every shortest chain to `v` is a shortest chain to some module at distance `d` that imports `v`, followed by `v`, and by induction `chain(u)` is the smallest shortest chain to `u` and `u` is the first such module, so `chain(u) + [v]` is the smallest shortest chain to `v`. A pair's chain must start in `from` and end in `to`; a shortest chain never passes through another module of `to` (it would end there sooner) or another module of `from` (it would start there), so the first module of `to` in discovery order ends the smallest shortest chain of the pair. A full walk discovers modules in the same order as one that stops at the first module of `to`, so one walk serves every `to` of a `from`.

Shortest cycle: a cycle through `name` is a shortest chain from `name` to some module `u` that imports `name`, followed by `name`. Modules leave the queue by distance, and within a distance in the order of their chains, so the first one that imports `name` gives the fewest imports and, among those, the smallest list.

Components: the node that finishes last in the first pass lies in a component that no other component has an arrow into. A search over the reversed graph from it therefore reaches exactly the nodes that reach it in the original graph, which are the nodes of its component. Removing them and starting again from the next unassigned node in reverse finishing order repeats the argument on what is left, so each search of the second pass collects one component. Tarjan's one-pass method finds the same components.

Ignores and modes: an ignore removes imports from the graph that one contract walks, so the walk finds the shortest chain that uses none of them, which is exactly "skip the import and look again".

### Complexity

- Time: O(I log I) after a change, to resolve and sort the I imports; then O(V log V + I R) per walk or cycle search, with R the ignores and exceptions of the contract checked — resolving an import tries at most 8 names, and sorting each module's targets costs O(I log I) in total; a walk visits each module and each import once, testing each import against the contract's R rules, and sorting the members or the reached modules costs O(V log V); the two passes for components visit each group and arrow twice. `check` runs one walk per distinct `from` name of each contract.
- Space: O(V + I) — the imports as written, the resolved lists, and per walk a parent map and a queue of at most V modules.

### Trade-offs

- Rebuilding the whole graph after a change is simple and correct, and costs O(I log I) per change followed by a question. A long session of single-module edits could instead re-resolve only the imports that a new module can capture: those that start with its name and a dot.
- One walk per `from` name, instead of one per pair, matters for layers: a contract of L layers has L(L-1)/2 pairs but only L-1 names to walk from.
- The two-pass method needs the reversed graph; Tarjan's algorithm finds the components in one pass with low-link values and no reversed copy, at the cost of a subtler invariant. Both are linear.
- Reachability by a breadth-first walk per name is the right tool for a few names. Checking many independence names against each other on a large graph could compute the component graph once and answer reachability between components instead.
- Direct mode is a lookup over the members' import lists and never walks; it is what a reviewer can check by reading one file, and it misses every break that goes through a module the contract does not name.

### Pitfalls and edge cases

- Resolution is by the longest declared start that ends at a dot: `lib.coreutils` is not inside `lib.core`, and `lib.core.Thing` goes to `lib.core` even when `lib` is declared too. An import of a package with no module of its own is unknown.
- An import that resolves to the importing module, such as a class defined in the same file, is not a dependency, and so a single module is never a cycle.
- A name covers its module and the modules below it. Imports between covered modules are inside the package, and a chain that comes back into the package lists nothing inside it.
- Transitive dependencies are sorted by distance first, and the distance counts from the nearest covered module.
- Components, not cycles, are reported: overlapping cycles form one entry.
- The shortest cycle is not the first cycle a depth-first search finds, and building the chain backwards from the end with the smallest module at each step does not give the smallest list: the comparison starts at the front.
- Layers forbid every lower-to-higher pair, not only neighbours, and allow every higher-to-lower import. Independence is checked in both directions, a forbidden import in one.
- A chain may start at any module of `from`: walking from the first member and through the others gives a longer chain.
- An ignore covers names, so it skips every import between the modules they cover; it belongs to one contract. Skipping imports must happen during the walk, or a second, longer chain stays hidden.
- Versions compare as numbers (`1.9` before `1.10`) with missing parts as zero (`3` equals `3.0`), and an exception is expired at its own version. `allow` with an equal version written differently changes nothing.
- The ratchet removes fixed entries from the baseline and never adds new breaks to it; the new rows come before the fixed ones.

### Language notes

- Sorting: Python compares strings and tuples by code point, TypeScript's `<` compares UTF-16 units, Java and Kotlin `compareTo` do the same, and Go and Rust compare bytes. All of them agree on the letters, digits, `_` and `.` that names use. TypeScript, Java and Kotlin need a small function to compare two rows element by element; Python's lists, Go's `slices.Compare` and Rust's `Vec<String>` compare that way already, and so do the version lists.
- Map order: the Go specification leaves the iteration order over maps unspecified, Rust's `HashMap` visits its entries in an arbitrary order, and Java's `HashMap` promises no order either, so those references sort every list built from a map. Python dictionaries, JavaScript's `Map` and the map that Kotlin's `mutableMapOf` returns keep insertion order, but the references sort anyway rather than rely on the order of calls.
- The queue: Python uses `collections.deque`, Java an `ArrayDeque`, Rust a `VecDeque`; TypeScript and Go use the discovery list itself as the queue, with a moving head index.
- Both depth-first passes use explicit stacks in every language, so a long chain of modules never reaches a recursion limit.
- Keys: TypeScript joins two names with a character that cannot be in a name (NUL) to key a map by a pair, and Go does the same for rows while it keys ignores and exceptions by a struct of two strings; Python uses tuples, Java `List` keys, Kotlin `Pair` keys, and Rust tuples of `String`.
- Empty answers: Go returns empty slices rather than `nil`, so that an empty answer is the list `[]`.
- Names: `check`, `ignore` and `allow` are not reserved in any of the six languages. Go exports `AddModule` and the rest, and Rust uses `add_module`.

## Further reading

- D. L. Parnas, "On the criteria to be used in decomposing systems into modules", Communications of the ACM 15(12), 1053–1058, 1972, [doi:10.1145/361598.361623](https://doi.org/10.1145/361598.361623): modularization as a way to make a system more flexible and easier to understand, and how much depends on the criteria used to divide it.
- E. W. Dijkstra, "The structure of the 'THE'-multiprogramming system", Communications of the ACM 11(5), 341–346, 1968, [doi:10.1145/363095.363143](https://doi.org/10.1145/363095.363143): a system built as hierarchical levels, where the hierarchy proved vital for verifying the design.
- R. Tarjan, "Depth-First Search and Linear Graph Algorithms", SIAM Journal on Computing 1(2), 146–160, 1972, [doi:10.1137/0201010](https://doi.org/10.1137/0201010): strongly connected components in time and space linear in the size of the graph.
- J. Lakos, *Large-Scale C++ Software Design*, Addison-Wesley, 1996: chapter 4 on cyclic and acyclic physical dependencies, and chapter 5 on levelization, including escalation and demotion.
- R. C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Pearson, 2017: chapter 14 on component coupling and the Acyclic Dependencies Principle, and chapter 22 on the Dependency Rule, that source code dependencies point only inward, toward higher-level policies. Hexagonal architecture (ports and adapters) aims at the same thing from another side: an application that can be developed and tested in isolation from its devices and databases.
- [Python Programming FAQ, "How can I have modules that mutually import each other?"](https://docs.python.org/3/faq/programming.html#how-can-i-have-modules-that-mutually-import-each-other): how a cycle of imports fails while a module is still running.
- [The Go Programming Language Specification, Import declarations](https://go.dev/ref/spec#Import_declarations): a package may not import itself, directly or indirectly.
- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html), item 11: major, minor and patch versions are compared numerically.
