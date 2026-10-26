# Accounts Merge: Explanation

## Overview

A is the number of accounts and E the total number of address entries. Treat accounts as nodes: an address listed by several accounts joins them, and each person is one connected component. Both approaches join each account to the first account that listed the same address, using union-find, then group the addresses by component and sort them; they differ only in how the union-find trees are kept.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| quick-union | brute | O(E * A + E log E) | O(E) | to see what goes wrong without balancing |
| union-find | optimal | O(E log E) | O(E) | default answer |

A depth-first search over a graph whose nodes are the addresses (each account linking its first address to the others) is the other common optimal answer; it has the same O(E log E) bound, dominated by the sorting, but needs adjacency lists.

## Approach: quick-union (Naive union-find over accounts that links roots without balancing or compression)

### Intuition

Remember, for every address, the first account that listed it. When a later account lists the same address, the two accounts belong to the same person, so merge their trees. Comparing against the first owner suffices: every account that lists the address gets merged with that one, and hence with each other.

### Algorithm

1. Give each account its own tree: `parent[i] = i`.
2. For each account `i` and each of its addresses: if the address has no owner yet, record `i`; otherwise find the roots of the owner and of `i`, and if they differ, link the owner's root under `i`'s root.
3. Group every account's addresses into a set keyed by the account's root.
4. For each group, output the root account's name followed by the sorted addresses.

### Correctness

Invariant: two accounts are in the same tree exactly when the addresses processed so far link them through a chain of shared addresses. Each merge joins two accounts that share an address, and every shared address causes one, since each listing after the first merges with the first owner. After all addresses, the trees are exactly the people. All accounts of a person carry the same name, so the root's name is the person's name, and the set removes repeated addresses before sorting.

### Complexity

- Time: O(E * A + E log E) — each address entry triggers a `find`, which can walk a chain of up to A accounts; sorting all groups costs O(E log E) in total. The generated inputs have one person with hundreds of accounts sharing a common address: each such account hangs the existing chain under itself, so the chain grows by one per account and every later `find` walks it.
- Space: O(E) — the owner map and the grouped address sets; the parent array adds O(A).

### Trade-offs

A small amount of code, and the structure is the right one. Only the tree shapes are wrong, and the naive linking makes the quadratic case easy to hit, exactly as in the generated inputs. Two small additions fix it.

### Pitfalls and edge cases

- Same name does not mean same person; only shared addresses link accounts.
- Deduplicate addresses: an address may appear in several accounts or twice in one.
- Sort by character codes: `.` and digits come before `@` and letters, which the default string sort of all four languages already does.

### Language notes

- Python: `dict.setdefault(address, i)` records the first owner and returns it in one call; a set per root removes duplicates before `sorted`.
- TypeScript: the default `sort()` compares UTF-16 code units, which is character-code order for these ASCII strings.
- Java: `putIfAbsent` returns the previous owner or `null`; a `TreeSet` both deduplicates and sorts with `String.compareTo`.
- Kotlin: `putIfAbsent(...) ?: continue` skips first listings; `groupBy(::find)` groups account indexes by root.

## Approach: union-find (Union by size with path compression over accounts)

### Intuition

Keep everything from the naive version and fix the trees: union by size hangs the smaller tree under the larger one, so no tree is deeper than log2(A), and path compression re-points every node on a `find` path at its root. With both, every operation costs amortized O(α(A)), and the sorting becomes the only part that is more than linear.

### Algorithm

1. Initialize `parent[i] = i` and `size[i] = 1`.
2. For each account `i` and each of its addresses: record `i` as the owner of a new address, or `union(owner, i)` for an address seen before.
3. `union` attaches the smaller root under the larger and adds the sizes; `find` compresses the path it walks.
4. Group addresses by root, sort each group, and put the root account's name in front.

### Correctness

Union by size only decides which root survives a merge, and path compression only shortens paths to the same root, so the sets are exactly those of the naive version, and its argument applies unchanged.

### Complexity

- Time: O(E log E) — the at most 2E finds cost O(E * α(A)) in total by Tarjan's analysis, which is effectively linear; sorting the groups costs O(E log E) and dominates.
- Space: O(E) — the owner map and the address groups; the two arrays add O(A).

### Trade-offs

The standard answer: near-linear merging with two small arrays, then one sort per person. The address-graph search reaches the same bound but builds adjacency lists for all addresses. Union-find over accounts (rather than over addresses) also keeps the arrays as small as the number of accounts.

### Pitfalls and edge cases

- Union with the first owner, not with every previous account that listed the address; the result is the same but the work is not.
- Take the name from any account of the group, for instance the root; all of them carry the same name.

### Language notes

- Python: `defaultdict(set)` collects each person's addresses; the name is read from the root account.
- TypeScript: a `DisjointSets` class with fields set in the constructor body (no parameter properties); `Map` keeps the groups in first-seen order, which does not matter for the comparator.
- Java: `computeIfAbsent(root, unused -> new TreeSet<>())` builds sorted, duplicate-free groups.
- Kotlin: `groupBy(sets::find)`, then `distinct().sorted()` per group, builds the answer in one expression.
