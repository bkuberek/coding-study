# Smallest String With Swaps: Explanation

## Overview

n is the length of `s` and p the number of pairs. The key fact: positions connected through a chain of pairs form a group whose characters can be rearranged in every possible way, and different groups never exchange characters. So the answer sorts each group's characters into the group's positions. Both approaches find the groups with union-find; α is the inverse Ackermann function, at most 4 in practice.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| quick-union | brute | O(p * n + n log n) | O(n) | to see the cost of unbalanced trees |
| union-find | optimal | O(n log n + p * α(n)) | O(n) | default answer |

Why every arrangement of a group is reachable: within a connected group, any two positions are joined by a path of pairs, and swapping along that path and back (a, b, then the next pair, and so on, then undoing all but the last) exchanges the two end characters while restoring everything in between. Arbitrary transpositions generate all permutations.

## Approach: quick-union (Naive union-find over positions, then sort each group)

### Intuition

Read the pairs into a union-find structure over positions, so positions in the same group end up with the same root. Then, for each group, collect its positions in increasing order and its characters in sorted order, and write the smallest character into the first position, the next into the second, and so on.

### Algorithm

1. `parent[x] = x` for every position.
2. For each pair `[a, b]`, find both roots; if they differ, link `a`'s root under `b`'s root.
3. Group the positions by root, scanning positions in increasing order.
4. For each group, sort its characters and assign them to its positions in order.
5. Return the joined characters.

### Correctness

After step 2, two positions share a root exactly when a chain of pairs joins them, so the groups are the connected components. Any string reachable by swaps keeps each group's multiset of characters on that group's positions, because a swap only exchanges characters within one group. Among all strings with these multisets, the smallest puts each group's characters in non-decreasing order along its positions: at the first position where a string differs from that one, it must hold a larger character of the same group. That string is reachable by the overview's argument, so it is the answer.

### Complexity

- Time: O(p * n + n log n) — each pair costs two finds, and without balancing a tree can be a chain of n positions; the generated inputs list a large star hub first, which builds exactly such a chain. Sorting the groups costs O(n log n) in total.
- Space: O(n) — the parent array, the groups and the character array.

### Trade-offs

The grouping and sorting steps are already optimal; only the union-find trees are not. On adversarial pair orders, the finds dominate everything else.

### Pitfalls and edge cases

- Sort the characters of each group, not its positions only; the positions must stay in increasing order.
- Pairs may repeat or join a position to itself; union-find ignores both naturally.
- A position in no pair is a group of one and keeps its character.

### Language notes

- Python: `defaultdict(list)` builds the groups; `zip(positions, sorted(...))` assigns the letters.
- TypeScript: `[...s]` splits the string into characters; the default `sort()` orders single lowercase letters correctly.
- Java: a `char[]` per group sorted with `Arrays.sort` avoids boxing.
- Kotlin: `s.indices.groupBy(::find)` keeps each group's positions in increasing order, because `groupBy` preserves encounter order.
- Go: strings are immutable, so the result is built in a `[]byte` copy and converted back with `string(letters)`. Indexing a string yields a `byte`, which is exact for the lowercase ASCII input, and `slices.Sort` sorts the bytes of each group. `for position := range len(s)` (Go 1.22 and newer) counts positions without decoding runes.
- Rust: `s.as_bytes()` borrows the letters and `to_vec()` makes the mutable copy, so each group sorts the original letters while the output is rewritten. `sort_unstable` is fine for plain `u8` values, because equal letters are indistinguishable, and `String::from_utf8` turns the bytes back into the answer.

## Approach: union-find (Union by size with path compression, then sort each group)

### Intuition

Same plan with a balanced, compressed union-find: union by size keeps trees at most log2(n) deep, and path compression flattens every path a `find` walks. The grouping then costs effectively linear time, and sorting the groups is the dominant step.

### Algorithm

1. `parent[x] = x`, `size[x] = 1` for every position.
2. For each pair, `union` the two positions: attach the smaller root under the larger and add the sizes.
3. Group, sort and assign exactly as in the naive version, using the compressing `find`.

### Correctness

Union by size and path compression change only the shape of the trees, not which positions share a root, so the groups and therefore the result are those of the naive version.

### Complexity

- Time: O(n log n + p * α(n)) — the 2p finds plus n more for grouping cost O((n + p) * α(n)) by Tarjan's analysis; sorting all groups costs O(n log n), which dominates.
- Space: O(n) — parent and size arrays, groups and the result.

### Trade-offs

Near-linear grouping and a single sort per group. Since there are only 26 letters, counting the letters of each group and writing them back in alphabetical order would bring the whole algorithm down to O(n * 26 + p * α(n)); for these sizes the comparison sort is simpler and fast enough. A depth-first search over the pairs finds the same groups in O(n + p) but needs adjacency lists.

### Pitfalls and edge cases

- Group positions in increasing order before assigning sorted characters; any other order puts the small characters in the wrong places.
- Use an iterative `find`; long chains can exceed recursion limits before compression shortens them.

### Language notes

- Python: `parent[x], x = root, parent[x]` compresses and advances in one tuple assignment.
- TypeScript: `DisjointSets` assigns its fields in the constructor body, with no parameter properties; a `Map` of position lists gathers the groups.
- Java: `computeIfAbsent(root, unused -> new ArrayList<>())` gathers positions; `new String(letters)` builds the result.
- Kotlin: `groupBy(sets::find)`, then `zip` of positions with sorted characters writes each group back.
- Go: `parent[x], x = root, parent[x]` is the tuple assignment of the Python version, `rootA, rootB = rootB, rootA` swaps the roots, and `groups` is a slice indexed by root instead of a `defaultdict`; roots with no members stay nil and are skipped by the loop's empty work.
- Rust: `find` takes `&mut [usize]` because it compresses paths, so it is called as its own statement before the group lists are pushed to, and `groups` is a `Vec<Vec<usize>>` indexed by root. `zip` stops at the shorter of the positions and the sorted letters, which have the same length.
