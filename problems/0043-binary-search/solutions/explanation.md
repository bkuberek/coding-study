# Binary Search: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-scan | brute | O(n) | O(1) | the array is tiny or unsorted, or as a correctness oracle |
| closed-range | optimal | O(log n) | O(1) | default answer for an exact-match lookup |
| lower-bound | optimal | O(log n) | O(1) | the same search must also answer "where would it go" or "first occurrence" |

## Approach: linear-scan (Scan every position)

### Intuition

Ignore the ordering and compare `target` with every element from left to right. The first equal element is the answer; reaching the end means the value is absent.

### Algorithm

1. For each index `i` from 0 to n - 1, if `nums[i] == target`, return `i`.
2. After the loop, return `-1`.

### Correctness

Every index is compared with `target` before the loop ends, so a matching index is never missed, and an index is returned only when its value equals `target`. Values are distinct, so the first match is the only match.

### Complexity

- Time: O(n) — one comparison per element in the worst case. The test generator places a present target in the back half of the array, so the scan reads at least n/2 elements at every seed.
- Space: O(1) — one loop index.

### Trade-offs

It is trivially correct and works on unsorted data, which is why it serves as the oracle. It throws away the one fact the problem gives you: the order. At n = 10^5 it costs up to 10^5 comparisons where a binary search needs 17.

### Pitfalls and edge cases

- An early exit on `nums[i] > target` is a valid optimization for sorted input, but it is still linear in the worst case.
- Return `-1`, not `0` or `null`, when the value is absent.

### Language notes

- Python: `nums.index(target)` does the same scan in C but raises `ValueError` when the value is missing.
- TypeScript: `nums.indexOf(target)` already returns `-1` when absent.
- Java and Kotlin: a plain index loop over `int[]` / `IntArray` avoids boxing; Kotlin's `nums.indexOf(target)` is the one-line equivalent.

## Approach: closed-range (Binary search on a closed range)

### Intuition

Because the array is sorted, one comparison with a middle element `nums[m]` settles the fate of a whole half: if `nums[m] < target`, every element at or left of `m` is too small; if `nums[m] > target`, every element at or right of `m` is too large. Discarding half of the candidates per step leaves one candidate after about log2(n) steps.

### Algorithm

1. Set `low = 0` and `high = n - 1`; the candidates are the indices in `[low, high]`.
2. While `low <= high`:
   1. Let `middle = low + (high - low) / 2`.
   2. If `nums[middle] == target`, return `middle`.
   3. If `nums[middle] < target`, set `low = middle + 1`; otherwise set `high = middle - 1`.
3. Return `-1`.

### Correctness

Invariant: if `target` is in `nums`, its index lies in `[low, high]`. It holds initially because the range is the whole array. When `nums[middle] < target`, sortedness puts every index `<= middle` below `target`, so moving `low` past `middle` keeps the invariant; the other branch is symmetric. Each iteration removes at least `middle` itself, so the range shrinks and the loop ends. When it ends with `low > high` the range is empty, so by the invariant `target` is absent.

### Complexity

- Time: O(log n) — each iteration at least halves the range `high - low + 1`, so there are at most floor(log2 n) + 1 iterations.
- Space: O(1) — three indices.

### Trade-offs

This is the classic answer and the clearest for an exact-match lookup, since it can stop as soon as it hits the target. It answers only "is it here, and where"; for "first position not less than target" or insertion points, the lower-bound form is easier to adapt without mistakes.

### Pitfalls and edge cases

- The loop condition must be `low <= high` with a closed range: `low < high` skips the last candidate (`[5]` with target 5 would return `-1`).
- Both updates must move past `middle` (`middle + 1`, `middle - 1`); `low = middle` can loop forever on a two-element range.
- `(low + high) / 2` overflows 32-bit integers when both are near 2^31. With n at most 10^5 it cannot happen here, but `low + (high - low) / 2` is the habit to keep.
- A one-element array and a target outside `[nums[0], nums[n - 1]]` both end with an empty range and return `-1`.

### Language notes

- Python: integers do not overflow, so `(low + high) // 2` is safe. Use `//`, not `/`, which produces a float.
- TypeScript: numbers are doubles, so `(high - low) >> 1` truncates to an integer; plain `/ 2` would produce `2.5` and an `undefined` element.
- Java and Kotlin: integer division truncates toward zero, which is what the midpoint needs since both bounds are non-negative. Kotlin's `when` with conditions replaces the `if` chain.

## Approach: lower-bound (Lower-bound search on a half-open range)

### Intuition

Instead of looking for `target` directly, look for the boundary between "less than `target`" and "at least `target`". The predicate `nums[i] >= target` is false for a prefix of the array and true for the rest, so its first true index can be found by halving. If that index holds `target`, it is the answer; otherwise `target` is absent and the index is where it would be inserted.

### Algorithm

1. Set `low = 0` and `high = n`; the boundary lies in the half-open range `[low, high)`, with `high = n` meaning "every element is smaller".
2. While `low < high`:
   1. Let `middle = (low + high) / 2`, rounded down.
   2. If `nums[middle] < target`, set `low = middle + 1`; otherwise set `high = middle`.
3. If `low < n` and `nums[low] == target`, return `low`; otherwise return `-1`.

### Correctness

Invariant: every index below `low` holds a value less than `target`, and every index at or above `high` holds a value at least `target`. It holds initially (both sets are empty). The first branch is justified because `nums[middle] < target` and sortedness put every index up to `middle` below `target`; the second because `nums[middle] >= target` puts every index from `middle` on at or above it. `middle` is strictly less than `high` when `low < high`, so either update shrinks the range, and the loop ends with `low == high`: the first index whose value is at least `target`. That index holds `target` exactly when `target` is present.

### Complexity

- Time: O(log n) — the range `[low, high)` halves on every iteration, so the loop runs at most ceil(log2(n + 1)) times, plus one final comparison.
- Space: O(1) — three indices.

### Trade-offs

It always runs the full log2(n) iterations, while the closed-range version may stop early on a hit, but the difference is a handful of comparisons. In exchange the loop has a single comparison and one shape that solves many problems: insertion points, first and last occurrence (see `first-last-position`), and "first value that satisfies a monotone condition" (see `koko-eating-bananas`). It is the template worth memorizing.

### Pitfalls and edge cases

- With a half-open range, `high` starts at `n`, the loop runs while `low < high`, and the "not smaller" branch sets `high = middle`, not `middle - 1`. Mixing the closed and half-open conventions is the most common source of bugs.
- `low` can end at `n` (every element is smaller than `target`); check `low < n` before reading `nums[low]`.
- The midpoint must round down so that `middle < high`; rounding up with `high = middle` would loop forever on a two-element range.

### Language notes

- Python: `bisect.bisect_left(nums, target)` is exactly this loop in C; the reference writes it out because the interview usually expects that.
- TypeScript: there is no standard library binary search; `(low + high) >>> 1` is an unsigned shift that floors the midpoint and cannot go negative.
- Java: `Arrays.binarySearch(nums, target)` returns the index when found and `-(insertionPoint) - 1` otherwise; it does not promise the first index when values repeat. `>>> 1` avoids overflow of `low + high`.
- Kotlin: `nums.binarySearch(target)` mirrors Java's contract; `ushr 1` is the unsigned shift.
