# Evaluate Division: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bfs-per-query | brute | O(Q·(V + E)) | O(V + E) | few questions; simplest to write in an interview |
| weighted-union-find | optimal | O((E + Q)·α(V)) | O(V) | many questions, or equations that arrive over time |

Every equation `a / b = v` is a weighted edge: from `a` to `b` with weight `v` and back with weight `1 / v`. Following a path multiplies the weights, and because the equations are consistent, every path between two variables gives the same product, namely their quotient. V is the number of distinct variables, E the number of equations and Q the number of questions.

## Approach: bfs-per-query (Search the ratio graph once per query)

### Intuition

To evaluate `c / d`, walk from `c` toward `d` through the graph, multiplying the edge weights. Any path will do, since all paths give the same product. A breadth-first search from `c` records, for each variable it reaches, the product along the path that reached it; when it reaches `d`, that product is the answer. If it never reaches `d`, the quotient is not determined.

### Algorithm

1. Build an adjacency map: for each equation `a / b = v`, store `graph[a][b] = v` and `graph[b][a] = 1 / v`.
2. For each question `c / d`:
   1. If `c` or `d` is not in the graph, answer `-1.0`.
   2. Otherwise run a breadth-first search from `c` with `product[c] = 1`; when visiting `x` along the edge to `y`, set `product[y] = product[x] * graph[x][y]`.
   3. Answer `product[d]` if `d` was reached, else `-1.0`.

### Correctness

By induction on the order of discovery, `product[x]` equals `c / x`: it holds for `c`, and if `product[x] = c / x` then `product[x] * (x / y) = c / y`. The search reaches `d` exactly when a chain of equations links `c` and `d`, which is exactly when the quotient is determined. A variable absent from every equation has no node and is never determined, which covers `x / x` for an unknown `x`.

### Complexity

- Time: O(Q·(V + E)) — building the graph is O(E), and each question runs one search that can visit every variable and edge.
- Space: O(V + E) — the adjacency map, plus the products and queue of one search.

### Trade-offs

The natural first answer and short to write. Each question repeats a search over its whole group, so many questions over a large group cost a quadratic amount of work; caching all quotients per group, or the union-find below, removes that repetition.

### Pitfalls and edge cases

- Check that both variables are known before searching; `x / x` for an unknown `x` is `-1.0`, not `1.0`.
- Store the reverse edge with weight `1 / v`; many questions need an equation backwards.
- Test for the target when a node is taken from the queue (or when it is discovered), not only for the start: `c / c` must return `1.0` for a known `c`.

### Language notes

- Python: `defaultdict(dict)` builds the adjacency map; `zip(..., strict=True)` pairs equations with values.
- TypeScript: nested `Map<string, Map<string, number>>`; iterating a `Map` yields `[key, value]` pairs.
- Java: `computeIfAbsent` creates inner maps; the weights are boxed `Double` values, which is fine at this size.
- Kotlin: `getOrPut` creates inner maps, and `val (a, b) = equation` destructures a two-element array.

## Approach: weighted-union-find (Union-find that stores each variable's ratio to its root)

### Intuition

Group the variables with a disjoint-set structure, one group per set of linked variables, and remember for each variable `x` its quotient with its parent, `x / parent(x)`. Multiplying these along the way up gives `x / root`. Then every question within a group is a single division: `c / d = (c / root) / (d / root)`. A question across groups is undetermined.

### Algorithm

1. For each equation `a / b = v`:
   1. Add `a` and `b` as their own roots with weight 1 if they are new.
   2. Find the roots: `ra` with `a / ra`, and `rb` with `b / rb`.
   3. If `ra != rb`, hang `ra` under `rb` with weight `ra / rb = v * (b / rb) / (a / ra)`.
2. For each question `c / d`: if either is unknown or their roots differ, answer `-1.0`; otherwise answer `(c / root) / (d / root)`.
3. `find(x)` walks to the root and then, from the node nearest the root back down to `x`, multiplies each node's weight by its parent's (which already points at the root) and makes the root its parent.

### Correctness

Invariant: `weight[x] = x / parent(x)` for every variable, and roots have weight 1. It holds for new variables. Path compression keeps it: when a node's parent becomes the root, its weight becomes the product of the weights on the old path, which is its quotient with the root. A merge keeps it: `a / rb = (a / ra) * (ra / rb)`, and `a / rb` must equal `(a / b) * (b / rb) = v * (b / rb)`, which gives the stored weight for `ra`. Merges happen exactly along equations, so two variables share a root exactly when a chain of equations links them; for those, `(c / root) / (d / root) = c / d`.

### Complexity

- Time: O((E + Q)·α(V)) — each equation and each question makes two `find` calls. With path compression alone (no union by rank) the bound is amortized O(log V) per call in the worst case; with union by rank as well it is α(V). In practice both are near-constant.
- Space: O(V) — one parent and one weight per variable.

### Trade-offs

Answers each question in near-constant time and supports equations that arrive in between questions. It also detects contradictions: an equation within one group whose stated value disagrees with `(a / root) / (b / root)`. The weight bookkeeping is easy to get backwards, so it takes more care than the search.

### Pitfalls and edge cases

- Get the merge formula right: hanging `ra` under `rb` needs `ra / rb`, not `rb / ra`. Checking it on a two-variable example is the fastest way to catch a flipped division.
- Compress paths from the top down (nearest the root first), so each parent's weight already refers to the root when a child uses it.
- Floating-point products drift slightly along long paths; the comparator accepts a relative error of `10^-5`.

### Language notes

- Python: two dicts; `find` returns the root together with `name / root`.
- TypeScript: two `Map`s; `find` returns a `[root, ratio]` tuple.
- Java: the maps are fields cleared at the start of each call, so `find` stays a small private method without extra parameters; after `find(x)`, `weight.get(x)` is `x / root`.
- Kotlin: `find` is a local function over two `HashMap`s; `path.asReversed()` walks the path from the root side without copying it.
