# Search Suggestions: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| filter-each-prefix | brute | O(L * m * n log n) | O(n) | a first, obviously correct version |
| binary-search | optimal | O(m * n log n + L^2 log n) | O(n) | default answer; one sort and no extra structure |
| trie-top-three | optimal | O(m * n log n + S) | O(26 * S) | many search words against the same products |

`n` is the number of products, `m` the length of the longest product, `S` the total length of all products and `L` the length of `searchWord`.

## Approach: filter-each-prefix (Filter and sort the products for every typed prefix)

### Intuition

Each entry of the answer is defined independently: the products that start with the typed prefix, alphabetically, at most three. Compute exactly that for every prefix.

### Algorithm

1. For each length `t` from 1 to `L`, let the prefix be the first `t` letters of `searchWord`.
2. Keep the products that start with the prefix, sort them and take the first three.
3. Return the list of these entries.

### Correctness

Each entry is computed straight from its definition: the filter keeps exactly the products with that prefix, sorting puts them in alphabetical order, and the first three are the ones to show (fewer if fewer match).

### Complexity

- Time: O(L * m * n log n) — for each of the `L` prefixes, the filter checks every product, and sorting the matches costs up to O(n log n) comparisons of up to `m` letters each.
- Space: O(n) — the filtered list of one prefix; the output holds at most `3L` names.

### Trade-offs

It is the clearest statement of the problem and a reliable oracle, but it filters and sorts from scratch for every letter, even though each prefix's matches are a subset of the previous prefix's.

### Pitfalls and edge cases

- Once no product matches a prefix, every longer prefix is empty too.
- Alphabetical order puts a word before its own extensions: `app` comes before `apple`.
- Products in the input are not sorted.

### Language notes

- Python: `sorted` on a generator expression; slicing `[:3]` never fails on short lists.
- TypeScript: the default `sort()` compares UTF-16 code units, which is alphabetical for lowercase letters.
- Java: `subList` is a view, so the reference copies it into its own `ArrayList`.
- Kotlin: `filter`, `sorted` and `take(3)` express the definition in one chain.
- Go: Python's `[:3]` forgives a short list and a slice expression does not, so the cut is `matches[:min(shown, len(matches))]` with the `min` builtin. `slices.Sort` orders strings byte by byte, which is alphabetical for lowercase letters, and a nil `matches` slices to nil, which the encoder writes as `[]`.
- Rust: `.iter().filter(..).collect::<Vec<&String>>()` collects borrows, so only the first three are cloned into the answer; `sort()` on `Vec<&String>` compares the strings, not the addresses. `take(SHOWN)` is the forgiving `[:3]`.

## Approach: binary-search (Sort once and binary-search each prefix)

### Intuition

In a sorted list, all products that start with a prefix form one contiguous block, and that block begins at the first product that is not alphabetically smaller than the prefix. So sort once, find that position by binary search, and the suggestions are the next three products, as long as they still start with the prefix.

### Algorithm

1. Sort the products.
2. For each prefix of `searchWord`, find `start`, the first index whose product is at least the prefix (lower bound). Because a longer prefix is never smaller, its block cannot start earlier, so each search begins at the previous `start`.
3. Take the products at `start`, `start + 1` and `start + 2` that start with the prefix.

### Correctness

A string that starts with prefix `p` is at least `p` and smaller than every string that is greater than `p` but does not start with it, so in sorted order the strings starting with `p` are consecutive and the first of them is the first string not smaller than `p`, if any string starts with `p` at all. Hence the first three products from the lower bound that start with `p` are exactly its three alphabetically smallest matches; the prefix check stops at the end of the block. Extending `p` to `p + c` gives a string at least `p`, so its lower bound is at or after `p`'s, which justifies starting the next search there.

### Complexity

- Time: O(m * n log n + L^2 log n) — sorting compares up to `m` letters per comparison; each of the `L` binary searches does O(log n) comparisons of up to `L` letters.
- Space: O(n) — the sorted copy of the products.

### Trade-offs

One sort and a few binary searches: fast, compact and the expected answer. It needs the full product list up front; inserting new products into a sorted array costs O(n) each, where a trie absorbs them in O(m).

### Pitfalls and edge cases

- The lower bound for a prefix with no matches points at a product that does not start with it (or past the end); the prefix check, not the index, decides what is shown.
- Comparing only the first `t` letters of products with the prefix while binary-searching works too, but plain string comparison against the prefix is simpler and correct.
- Copy before sorting when the caller's list must stay untouched.

### Language notes

- Python: `bisect_left(ordered, prefix, start)` is the lower bound with a starting index.
- TypeScript: `<` on strings compares code units; `(low + high) >>> 1` halves without floating point.
- Java: `products.clone()` keeps the input intact before `Arrays.sort`; `compareTo` drives the lower bound.
- Kotlin: `sorted()` returns a new list, and `<` on strings uses `compareTo`; `ushr` is the unsigned shift.
- Go: `slices.BinarySearch(ordered[start:], prefix)` is the lower bound (it returns the first position whose element is not less than the target, plus a found flag), and the subslice stands in for Python's `lo=start`, so the offset is added back to `start`. `slices.Clone` sorts a copy and leaves the caller's slice in its order.
- Rust: `ordered[start..].partition_point(|product| product.as_str() < prefix)` is the lower bound on a sorted slice, again relative to `start`. The function owns `products`, so it sorts that vector in place and needs no copy.

## Approach: trie-top-three (Trie whose nodes keep their three smallest products)

### Intuition

Typing one letter at a time is walking one trie edge at a time. If every trie node already knows the three alphabetically smallest products below it, each typed letter costs one step. Inserting the products in sorted order fills those lists for free: the first three products to pass through a node are its three smallest.

### Algorithm

1. Sort the products and insert them into a trie in that order; on the way down, append the product to every node it passes whose list holds fewer than three products.
2. Walk the trie along `searchWord`. After each letter, the current node's list is the entry; once the walk falls off the trie, every remaining entry is empty.

### Correctness

The products passing through a node are exactly those that start with the node's prefix. They are inserted in alphabetical order, so the first three of them to arrive, the ones kept, are the three smallest (or all of them, if fewer). Walking the trie along `searchWord` reaches, after `t` letters, the node of the first `t` letters if any product starts with them, and no node otherwise.

### Complexity

- Time: O(m * n log n + S) — the sort, plus one step per letter of every product while inserting; each query letter is then O(1) (copying at most three names).
- Space: O(26 * S) — at most one node per letter of the products, each with 26 slots and a list of at most three names.

### Trade-offs

It answers each typed letter in constant time and handles new products without re-sorting (insert keeps the lists, but then they must be updated by comparison instead of by order). For a single search word it uses far more memory than the binary search for the same result.

### Pitfalls and edge cases

- Inserting unsorted products and keeping the first three gives arbitrary suggestions, not the smallest.
- After the walk leaves the trie it must stay off: a later letter must not match a child of some unrelated node.
- Return copies of the node lists so the caller cannot modify the trie.

### Language notes

- Python: a node class with `__slots__`, and `list(node.smallest)` returns a copy.
- TypeScript: `??=` creates a missing child while walking; spreading `[...node.smallest]` copies.
- Java: each node holds an `ArrayList<String>` with capacity 3, copied into the result.
- Kotlin: `searchWord.map { ... }` builds one entry per letter, and `node?.children?.get(...)` stays null once the walk has left the trie.
- Go: each node has `children [26]*node` and a `smallest []string` that grows to at most three with `append`; `slices.Clone` copies it into the answer (a nil slice stays nil and encodes as `[]`). The cursor is a `*node` that becomes `nil` when the walk leaves the trie, and stays `nil` after that.
- Rust: `Node` derives `Default`, so `get_or_insert_with(Box::default)` makes a missing child. The cursor is an `Option<&Node>` that `and_then(|node| node.children[..].as_deref())` advances, and `map_or_else(Vec::new, ..)` yields the empty list once it is `None`. Sorting the owned `products` first is what makes each node's first three entries the smallest.
