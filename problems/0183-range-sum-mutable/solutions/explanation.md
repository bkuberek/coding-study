# Range Sum Query With Updates: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| direct-scan | brute | O(1) per update, O(n) per sumRange | O(n) | updates vastly outnumber queries, or as a correctness oracle |
| fenwick-tree | optimal | O(log n) per call | O(n) | default answer for sums: shortest code, smallest constant |
| segment-tree | optimal | O(log n) per call | O(n) | the operation is not invertible (min, max, gcd) or you need range updates later |

`n` is the length of the array. The generated sequences make `n` calls, half of them queries, so the direct scan costs O(n^2) per sequence and both trees O(n log n). Prefix sums (Range Sum Query) would invert the trade-off of the direct scan: O(1) queries, O(n) updates.

## Approach: direct-scan (Store the array and add up each range)

### Intuition

Keep the array as it is. An update writes one cell; a query adds up the range from scratch.

### Algorithm

1. The constructor copies `nums`.
2. `update(index, value)`: `nums[index] = value`.
3. `sumRange(left, right)`: add `nums[left..right]` into a 64-bit total and return it.

### Correctness

The stored array always equals the current array, because every update is applied immediately, and a query adds exactly the requested positions.

### Complexity

- Time: O(1) per update, O(n) per sumRange — a query can span the whole array.
- Space: O(n) — the copy of the array.

### Trade-offs

Trivial and perfect if queries are rare. With a mix of both operations, every query repeats work that a tree of partial sums would have kept.

### Pitfalls and edge cases

- Copy the input array; the caller may keep using it.
- Sums reach 10^10 in absolute value: accumulate in a 64-bit integer.

## Approach: fenwick-tree (Fenwick tree of partial sums)

### Intuition

A Fenwick tree (binary indexed tree) stores, at 1-based index `i`, the sum of a block of `lowbit(i) = i & -i` consecutive values that ends at position `i`. Every prefix `1..p` splits into at most `log2 n` such blocks, found by repeatedly stripping the lowest set bit of `p`; and every position is contained in at most `log2 n` blocks, found by repeatedly adding the lowest set bit. A range sum is the difference of two prefix sums.

### Algorithm

1. Build: copy the values into `tree[1..n]`, then for `i = 1..n` add `tree[i]` into `tree[i + lowbit(i)]` when that index exists. This builds every block sum in O(n).
2. `update(index, value)`: compute `delta = value - values[index]`, store the new value, and for `i = index + 1, i + lowbit(i), ...` while `i <= n`, add `delta` to `tree[i]`.
3. `prefix(p)`: for `i = p, i - lowbit(i), ...` while `i > 0`, add `tree[i]`.
4. `sumRange(left, right) = prefix(right + 1) - prefix(left)`.

### Correctness

The block of index `i` is `(i - lowbit(i), i]`. Stripping lowest bits from `p` produces indexes whose blocks are adjacent and disjoint and together cover `(0, p]`, so step 3 adds every value of the prefix exactly once. The indexes visited in step 2, `i, i + lowbit(i), ...`, are exactly the indexes whose block contains position `index + 1`, so adding `delta` to each keeps every block sum correct. The linear build pushes each completed block into its parent block, the next index that contains it, which produces the same sums as `n` updates on an all-zero tree.

### Complexity

- Time: O(log n) per call — both loops change one bit of `i` per step, at most `log2 n + 1` steps; the build is O(n).
- Space: O(n) — `n + 1` block sums plus the current values (to compute the delta).

### Trade-offs

The shortest and fastest structure for prefix sums with point updates, which is why it is the default here. It needs an invertible operation (subtraction turns prefixes into ranges), so it does not answer range minimum queries; a segment tree does.

### Pitfalls and edge cases

- Fenwick trees are 1-based: position `index` lives at tree index `index + 1`, and index 0 is never used.
- Store the current values, or compute the delta from a range query: an update must add `value - old`, not `value`.
- `i & -i` relies on two's complement; it is correct for every positive `int`.

### Language notes

- Python: integers are unbounded; `i & -i` works the same as in fixed-width languages for positive `i`.
- TypeScript: block sums stay below 2^53, so plain `number`s are exact; `i & -i` is a 32-bit operation, fine for `n <= 10^5`.
- Java: `long[]` block sums; `(long) value - values[index]` computes the delta in 64 bits.
- Kotlin: `i and -i` replaces `i & -i`; the reference names it `lowBit` for readability.

## Approach: segment-tree (Iterative segment tree)

### Intuition

Put the values in the leaves of a complete binary tree stored in an array: leaf `i` at index `n + i`, and every internal node `v` holds the sum of its children `2v` and `2v + 1`. An update rewrites one leaf and the `log n` ancestors above it. A query climbs from both ends of the range at once, adding a node whenever the range boundary cuts between it and its sibling.

### Algorithm

1. Build: place the values at `tree[n..2n - 1]`, then fill `tree[v] = tree[2v] + tree[2v + 1]` for `v = n - 1` down to 1.
2. `update(index, value)`: set the leaf `n + index`, then recompute each ancestor `v = v / 2` up to the root.
3. `sumRange(left, right)`: keep a half-open interval `[low, high) = [left + n, right + n + 1)`. While `low < high`: if `low` is odd, add `tree[low]` and move `low` right; if `high` is odd, move `high` left and add `tree[high]`; then halve both.

### Correctness

Invariant of the query loop: the answer equals the total added so far plus the sum of the leaves under the nodes in `[low, high)` at the current level. An odd `low` is a right child whose parent also covers a node outside the range, so it is added on its own and skipped; likewise an odd `high` means the node just left of it is a left child whose parent sticks out. After those adjustments `low` and `high` are even, so the nodes in `[low, high)` pair up exactly into their parents `[low / 2, high / 2)`. The interval shrinks every level and the loop ends with the full sum. Updates keep every internal node equal to the sum of its children by recomputing exactly the nodes on the leaf's path.

### Complexity

- Time: O(log n) per call — one step per level, about `log2 n` levels; the build is O(n).
- Space: O(n) — `2n` node sums.

### Trade-offs

A little more code than a Fenwick tree for sums, but it generalizes: replace `+` by `min`, `max` or `gcd` and it still works, because it never needs subtraction; with lazy propagation it also supports range updates. The bottom-up form used here works for any `n`, not only powers of two, because addition is associative and commutative.

### Pitfalls and edge cases

- Use a half-open interval (`right + n + 1`) or carefully handle the inclusive end; mixing the two is the usual off-by-one.
- Recompute ancestors from the children, not by adding a delta, unless you also store the old value.
- With `n = 1`, the tree is `[unused, value]` and both loops still work.

### Language notes

- Python: `tree = [0] * n + nums` builds the leaves in one expression; `//= 2` climbs a level.
- TypeScript: `>>= 1` halves indexes below 2^31 exactly.
- Java: `long[] tree = new long[2 * n]`; `tree[low++]` and `tree[--high]` express the moves compactly.
- Kotlin: `(low and 1) == 1` needs the parentheses because the infix `and` binds more loosely than `==`.
