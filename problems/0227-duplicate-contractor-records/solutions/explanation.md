# Duplicate Contractor Records: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| union-find | optimal | O(L + n log n) | O(n + L) | default answer |

`n` is the number of records and `L` the total length of the names and tax ids.

## Approach: union-find (Union records that share a normalized name or tax id)

### Intuition

Records are nodes, a shared key is an edge, and the groups are connected components. A map from key to first record turns every key into one union.

### Algorithm

1. Normalize the name and the tax id of every record.
2. For each non-empty key, in record order: if some earlier record had the same key (of the same kind), union this record with it; otherwise remember this record as the key's first.
3. Group the records by the root of their set, walking the indices in order.
4. Keep the groups of two or more records.

### Correctness

Two records that share a key end in one set, because both are unioned with the key's first record. Unions only follow shared keys, so a set is exactly a connected component of the match relation. Walking the indices in increasing order emits each group sorted, and the groups ordered by their smallest index. Empty keys are never stored, so they match nothing, and names and tax ids live in separate key spaces.

### Complexity

- Time: O(L + n log n) — normalizing reads every character once; at most 2n unions and n finds with path halving cost O(log n) amortized each.
- Space: O(n + L) — the parent array and the key maps.

### Trade-offs

Comparing every pair of records and running a graph search is O(n^2). Union by size makes finds nearly constant. A bipartite graph of records and keys with a breadth-first search is also linear, and equally good; union-find is shorter and also handles records that arrive one at a time.

### Pitfalls and edge cases

- Legal-form words are dropped only at the end of a name (`h4`).
- Names that normalize to nothing, and tax ids with the wrong number of digits, must not match each other (`h2`, `h3`, `h10`).
- A name and a tax id share no key space (`h11`).
- A record that links two existing groups, by name and by tax id (`h9`).
- Group order: by smallest index (`h5`).
- Digits are kept in names and separators split words (`h7`).
- Identical records (`h8`).
- Locale-dependent lowercasing, such as the Turkish dotless `i` in Java.

### Language notes

- Python: `name.lower()` and `re.split(r"[^a-z0-9]+", ...)`; a `dict` keeps insertion order, so grouping by root returns the groups by smallest index. Keys are tuples such as `("name", key)` and `("tax", key)`.
- TypeScript: `toLowerCase()` is locale-independent; `split(/[^a-z0-9]+/).filter((word) => word.length > 0)`; a `Map<number, number[]>` keyed by root keeps insertion order, so the groups come out by smallest index.
- Java: use `name.toLowerCase(Locale.ROOT)`: the default locale can lowercase `I` to a dotless `ı` (Turkish), so `INC` would not match `inc`. `split("[^a-z0-9]+")` yields a leading empty string when the name starts with a separator, so skip empty words. Two `HashMap<String, Integer>` hold the first record of each key, `int[] parent` is the union-find, and a `LinkedHashMap<Integer, List<Integer>>` collects the groups in order.
- Kotlin: `lowercase()` uses `Locale.ROOT`. `split(Regex("[^a-z0-9]+")).filter { it.isNotEmpty() }`, `IntArray(n) { it }` for the parents, and `(0 until n).groupBy { find(it) }.values.filter { it.size > 1 }`, because `groupBy` keeps first-seen order.
