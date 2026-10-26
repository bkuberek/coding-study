# First and Last Position: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-scan | brute | O(n) | O(1) | the array is tiny, or as a correctness oracle |
| find-then-expand | intermediate | O(log n + k) | O(1) | the target is known to occur only a few times |
| two-bounds | optimal | O(log n) | O(1) | default answer |

`k` is the number of occurrences of `target`.

## Approach: linear-scan (Scan the whole array)

### Intuition

Walk the array once. The first time `target` appears is the first position, and the last time it appears is the last position.

### Algorithm

1. Set `first = last = -1`.
2. For each index `i`, if `nums[i] == target`: set `first = i` if it is still `-1`, and always set `last = i`.
3. Return `[first, last]`.

### Correctness

Every index is visited. `first` is assigned only at the first matching index and never again; `last` is overwritten at every match, so it ends at the last one. With no match both stay `-1`.

### Complexity

- Time: O(n) — the loop always visits all n elements.
- Space: O(1) — two indices.

### Trade-offs

Correct for unsorted arrays too, which makes it the oracle. It ignores the ordering, so it reads all 10^5 elements where about 34 probes suffice.

### Pitfalls and edge cases

- An empty array returns `[-1, -1]` without reading anything.
- Do not stop at the first match: the last position may be far away.

### Language notes

- Kotlin: `indexOfFirst` and `indexOfLast` with the same predicate return `-1` when nothing matches, which is exactly the required sentinel.
- Python: `nums.index(target)` finds the first position in C but raises `ValueError` when absent.

## Approach: find-then-expand (Binary search one occurrence and walk outwards)

### Intuition

A plain binary search lands on some occurrence of `target`, not necessarily the first or the last. Equal values are contiguous, so walking left and right from that hit until the value changes finds the whole block.

### Algorithm

1. Binary search for any index `middle` with `nums[middle] == target`; if there is none, return `[-1, -1]`.
2. Move `first` left from `middle` while the element before it equals `target`.
3. Move `last` right from `middle` while the element after it equals `target`.
4. Return `[first, last]`.

### Correctness

The binary search is correct on a non-decreasing array: when `nums[middle] < target` no occurrence lies at or left of `middle`, and symmetrically. Because the array is sorted, all occurrences form one contiguous block containing the hit, and the two walks stop exactly at the block's ends.

### Complexity

- Time: O(log n + k) — the search is logarithmic, and the walks visit every occurrence once. The test generator makes `target` fill between n/4 and n/2 positions, so on those inputs this is linear.
- Space: O(1) — a few indices.

### Trade-offs

It is the answer many candidates give first, and it is fine when duplicates are rare. Its worst case is an array made almost entirely of `target`, where it degrades to a linear scan; recognizing that and switching to two bound searches is the point of the problem.

### Pitfalls and edge cases

- Bounds checks inside the walks (`first > 0`, `last < n - 1`) prevent reading outside the array when the block touches an end.
- The walks compare with `target`, not with `nums[middle]` of a later iteration.

### Language notes

- Kotlin: `IntArray.binarySearch(target)` returns some matching index or a negative value; with duplicates it does not promise which match, which is fine because the walks fix that.
- Java: `Arrays.binarySearch` has the same contract; the reference writes the loop out to keep the four languages aligned.

## Approach: two-bounds (Lower-bound and upper-bound searches)

### Intuition

Turn both ends into "first index where a monotone condition becomes true". The first occurrence is the first index with `nums[i] >= target`. The last occurrence is one before the first index with `nums[i] > target`. One binary search template, called with two predicates, answers both in logarithmic time no matter how many copies of `target` there are.

### Algorithm

1. `first = firstIndex(nums[i] >= target)`, using the half-open search: `low = 0`, `high = n`; while `low < high`, if the predicate holds at `middle` set `high = middle`, else `low = middle + 1`.
2. If `first == n` or `nums[first] != target`, return `[-1, -1]`.
3. `afterLast = firstIndex(nums[i] > target)`.
4. Return `[first, afterLast - 1]`.

### Correctness

On a non-decreasing array each predicate is false for a prefix and true for the rest, and the search keeps the invariant "predicate false before `low`, true from `high` on", so it returns the boundary. The first boundary is where values reach `target`; if that position does not hold `target`, no position does. Otherwise every index in `[first, afterLast)` holds a value that is at least `target` and not greater than it, that is, exactly `target`, and no index outside that range does.

### Complexity

- Time: O(log n) — two binary searches of at most about log2(n) + 1 iterations each, independent of k.
- Space: O(1) — indices only.

### Trade-offs

This is the expected answer. The same two bounds also give the number of occurrences (`afterLast - first`) and insertion points, so it is worth knowing as a reusable helper. It always runs both searches in full, a few more probes than a lucky early stop, which never matters.

### Pitfalls and edge cases

- Use the predicate `> target` for the second search instead of searching for `target + 1`: with `target` at the top of the 32-bit range, `target + 1` overflows.
- `first` can equal `n` (every value is smaller); check it before reading `nums[first]`.
- An empty array makes both searches return 0 immediately, and the first check returns `[-1, -1]`.

### Language notes

- Python: `bisect.bisect_left(nums, target)` and `bisect.bisect_right(nums, target)` are exactly the two bounds; the reference spells out one helper that takes the predicate.
- TypeScript: the predicate is an arrow function; V8 inlines such small closures well, so the abstraction is nearly free.
- Java: a boolean `strict` flag selects `>=` or `>` without allocating a lambda per call.
- Kotlin: an `inline` function with a lambda parameter is compiled into each call site, so `firstIndex(nums) { it > target }` costs the same as a hand-written loop.
