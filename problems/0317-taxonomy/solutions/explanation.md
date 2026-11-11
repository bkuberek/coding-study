# Taxonomy: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| adjacency-walks | optimal | O(parents) per insert; O(V + E) per walk, cycle check or expansion | O(V + E) | default answer; one pair of adjacency sets serves all four levels |

Here `V` is the number of concepts and `E` the number of broader links.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Keep each concept's parents and children as sets | `label`, `up` (parents) and `down` (children): everything else is a walk over these |
| 2 | Refuse a link that closes a loop; define "lowest" as minimal | nothing new: a cycle check is an upward walk, the lowest common ancestors come from two upward walks |
| 3 | Labels and expansion | `alts` and an `index` from the normalized form of a label to the set of concepts that carry it |
| 4 | Stable ids, replacements and two schemes | `gone` (retired id to replacement) and `same` (exact matches, one set per concept); the scheme is read from the id |

The early choice that keeps the later levels cheap is to store both directions of every link from the start. A solution that stores only the parent of each concept answers level 1 slowly (every `narrower` or `descendants` call scans all concepts), and one that stores a single parent has to be rewritten to hold several. Level 4 adds one rule to every method (resolve the ids first), and it costs one line per method when ids are resolved in a helper, instead of rewriting the data.

## Approach: adjacency-walks (Parent and child sets with breadth-first walks)

### Intuition

A taxonomy with several parents is a directed acyclic graph, and every question in the problem is a reachability question on it: "what is above this concept" (follow `up`), "what is below" (follow `down`), "would this link close a loop" (is the new child above the new parent). A breadth-first walk answers all of them, and it also gives the order the statement asks for: the level at which the walk first meets a concept is its shortest distance. Labels, replacements and mappings are dictionaries that sit beside the graph and never change its shape.

### Algorithm

1. Level 1: `up[c]` is the set of parents of `c` and `down[c]` the set of its children; `addConcept` fills both. `ancestors` walks `up` one level at a time: the next level is every unseen parent of the current level, sorted by id. A `seen` set keeps a concept from being listed twice. `descendants` is the same walk over `down`. `roots` are the concepts with an empty `up`.
2. Level 2: `addBroader(n, b)` is refused when `n == b` or when `n` is among the concepts reached by walking up from `b`. For `lowestCommonAncestors(x, y)`, collect `A = {x} + ancestors(x)` and `B = {y} + ancestors(y)`, let `C = A ∩ B`, and keep every `c` in `C` that has no child in `C`.
3. Level 3: normalize a label (trim, collapse runs of spaces, fold `A` to `Z`) and keep `index[normalized]`, a set of concept ids, for every preferred and alternative label. `findByLabel` reads the set, `expand` starts a downward walk from all the matching concepts at once with one `seen` set, and `addAltLabel` compares the normalized label with the normalized labels the concept already has.
4. Level 4: `rename` replaces the label and appends the old one to `alts`, unless it normalizes to the same text as the new one. `deprecate` checks its statuses in order, removes the concept from its parents' `down` sets, moves its `same` partners to the replacement and records `gone[concept] = target`. A helper `follow` walks `gone` until it reaches a concept that is not retired, and rewrites the entries it passed to point at the end; every method calls it on every id it receives. `translate` keeps a concept that is already in the target scheme and otherwise collects the partners in `same[concept]` that are in the target scheme.

### Correctness

Breadth-first order: when the walk dequeues a level, the next level holds the unseen neighbours of it. A concept is first seen at the smallest level that contains one of its neighbours, so by induction on the level it is first seen at the length of the shortest path from the start. Sorting each level by id gives distance first, then id. The `seen` set makes the walk finish on any finite graph and list each concept once, whatever the number of paths.

Cycle check: adding the link `n` under `b` creates a cycle exactly when there is already a path from `b` up to `n`, or `n == b`. If `n` is not above `b`, then no path leads from `n` through the new link back to `n`, so the graph stays acyclic.

Lowest common ancestors: let `C` be the common ancestors of `x` and `y` (counting each as its own ancestor). `C` is closed upward: an ancestor of a member is an ancestor of both `x` and `y`. A member `c` is lowest when no other member lies below it. Suppose some member `d` lies below `c`. The path from `d` up to `c` ends with a link from a child `k` of `c` to `c`; `k` is an ancestor of `d` (or is `d`), hence of `x` and `y`, so `k` is in `C`. So "some member below `c`" is equivalent to "some child of `c` is a member", and the children test is enough.

Replacements: `gone` maps each retired id to the concept it was replaced by when it was retired, and that concept was not retired then. A later retirement extends the chain by one link, in the direction of newer ids only, so the chain is finite and cannot return to a retired id: `deprecate(c, r)` refuses `r` that resolves to `c`, and `c` was not retired before. Compression only shortens a path to its own end.

### Complexity

- Time: O(parents) per insert; O(V + E) per walk, cycle check or expansion — an insert touches each listed parent once; a walk visits every concept and every link in its reach once, and the per-level sorts add O(V log V) at most; the cycle check and the intersection of two walks are O(V + E); expansion is one walk from all matching concepts at once.
- Space: O(V + E) — the sets `up` and `down` hold each link twice, and the label index, the alternative labels, `gone` and `same` hold at most one entry per label, retired concept or match.

### Trade-offs

- A cycle check costs a walk up from the new parent. A dynamic topological order (Pearce and Kelly) lets most links be accepted in O(1), at the price of keeping an order up to date. For a taxonomy edited by people the walk is fast enough: a taxonomy is shallow.
- Descendants are recomputed for every `expand`. Caching the descendant set of each concept makes a repeated expansion O(answer), but every new link or removed link invalidates the sets of all the ancestors of the child.
- Lowest common ancestors by two full walks is the simplest and works on any DAG. For many queries on a fixed taxonomy, an Euler tour with a range minimum answers a tree in O(1), but a DAG has no such tour, which is the point of the problem.
- Resolving ids in one helper keeps level 4 small. The alternative, rewriting every link that mentions a retired id when it is retired, makes later calls cheaper and the retirement much more complex, because the rewrite can close a cycle.

### Pitfalls and edge cases

- Depth first is not nearest first. In a DAG a depth-first walk reaches a concept by a long path before a short one; the statement asks for the shortest distance. A sort by id ignores the distance, and the longest-path distance is also wrong when a link is a shortcut.
- A diamond lists its bottom concept twice unless a `seen` set guards the walk.
- In a DAG the lowest common ancestor is a set. Taking the deepest common ancestor, the first one, or all of them are all wrong; the hidden cases at level 2 have a lowest ancestor that is shallower than another one.
- A concept is its own ancestor in `lowestCommonAncestors`, but not in `ancestors`.
- The statuses have a fixed order, and a refused call changes nothing. `addConcept` with a parent list that holds one unknown id adds nothing, not even the known parents.
- Checking only the direct parents of the new parent finds two-concept loops and misses longer ones. A rejected link must not be kept.
- Normalization is applied to both sides. `a b` and `ab` are different labels, `  A  B ` and `a b` are the same one, and a label that is empty after trimming is not stored.
- `rename` to a label that already is an alternative label promotes it instead of keeping both; a rename that changes only the case adds nothing to `alts`.
- A retired id must work in every method, including as a parent when adding a concept, and must never appear in an answer.
- Exact matches are symmetric but not followed in chains: `translate` looks one step from the concept, even though SKOS declares `skos:exactMatch` transitive.
- The scheme is the text before the first colon, so `x:y:z` is in `x`.
- Recursion depth: the hidden cases hold chains of 1,300 and 1,500 concepts, and the generated case a chain of 50,000.

### Language notes

- Python sorts with `sorted`, whose string comparison is by code point; TypeScript's default `sort()` compares UTF-16 units, Java and Kotlin `compareTo` do the same, Go and Rust compare bytes. All of these agree on printable ASCII.
- `lower()`, `toLowerCase(Locale.ROOT)`, `lowercase()`, `strings.ToLower` and `to_ascii_lowercase` all fold `A` to `Z` on ASCII text. The statement fixes ASCII, so locale-sensitive folding (the Turkish dotless i) never shows up; use the root locale anyway in Java.
- Sets are `set`, `Set`, `HashSet`, `map[string]bool` and `HashSet<String>`. None of them keeps an order, so every list that the statement orders is sorted explicitly before it is returned.
- Rust methods take `&mut self` everywhere, because resolving an id compresses the chain of replacements. Parameters are owned `String` and `Vec<String>` as the bridge requires, so helpers take `&str`.
- Go and Rust copy a set before changing the map they read it from (for instance when moving the partners of a retired concept), and Rust loops over a cloned id while pushing to the queue it came from.

## Further reading

- [SKOS Simple Knowledge Organization System Reference, W3C Recommendation, 2009](https://www.w3.org/TR/skos-reference/): concepts (section 3), concept schemes (section 4), lexical labels and their integrity conditions (section 5, S13 and S14), semantic relations and why `broader` is not transitive (section 8), mapping properties and `skos:exactMatch` (section 10).
- [SKOS Primer, W3C Working Group Note](https://www.w3.org/TR/skos-primer/): an introduction with worked examples of concepts, labels and hierarchies.
- [RDF 1.1 Concepts and Abstract Syntax](https://www.w3.org/TR/rdf11-concepts/): the data model that SKOS is written in.
- A. B. Kahn, "Topological sorting of large networks", Communications of the ACM, 1962, and D. J. Pearce and P. H. J. Kelly, "A dynamic topological sort algorithm for directed acyclic graphs", ACM Journal of Experimental Algorithmics, 2006: the cycle check and how to avoid a walk for most inserts.
