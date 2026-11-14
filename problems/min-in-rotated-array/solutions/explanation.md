# Minimum in Rotated Sorted Array: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-scan | brute | O(n) | O(1) | the array is tiny, or as a correctness oracle |
| compare-with-right | optimal | O(log n) | O(1) | default answer |

## Approach: linear-scan (Scan for the smallest value)

### Intuition

The minimum of any array is found by looking at every element once and remembering the smallest so far. The rotation does not matter.

### Algorithm

1. Set `smallest = nums[0]`.
2. For each value in `nums`, if it is smaller than `smallest`, replace `smallest`.
3. Return `smallest`.

### Correctness

After processing the first `k` elements, `smallest` is the minimum of those `k` elements (induction on `k`). After all n elements it is the minimum of the array.

### Complexity

- Time: O(n) — every element is compared once, at every seed, because the scan cannot know it has seen the minimum until it has seen everything.
- Space: O(1) — one running value.

### Trade-offs

Correct for any input, including arrays that are not rotated-sorted at all, and therefore the oracle. A slightly smarter linear scan stops at the first drop (`nums[i] < nums[i - 1]`), but its worst case is still n steps.

### Pitfalls and edge cases

- Initialize with `nums[0]`, not with 0 or a sentinel that might be smaller than every value.
- A one-element array is its own minimum.

### Language notes

- Python: `min(nums)` is the idiomatic one-liner and runs in C; the reference spells out the loop to show the work.
- TypeScript: `Math.min(...nums)` spreads every element into arguments and can throw `RangeError` for very long arrays; a loop is safe.
- Kotlin: `nums.min()` (Kotlin 1.7+ returns non-null for non-empty arrays and throws on empty) is the idiomatic version.
- Go: `slices.Min(nums)` (Go 1.21 and newer) is the one-liner; it panics on an empty slice, which the constraints exclude.
- Rust: `nums.iter().min()` returns an `Option<&i32>`, so the one-liner needs an `unwrap`; the reference spells out the loop.

## Approach: compare-with-right (Binary search against the right end)

### Intuition

Compare a middle element with the last element of the current range. If `nums[middle] > nums[high]`, the values must drop somewhere between them, so the minimum lies strictly to the right of `middle`. Otherwise `nums[middle..high]` increases, so nothing to the right of `middle` is smaller than `nums[middle]`, and the minimum is `middle` or to its left. Either way half of the range goes away.

### Algorithm

1. Set `low = 0`, `high = n - 1`.
2. While `low < high`:
   1. Let `middle = (low + high) / 2`, rounded down.
   2. If `nums[middle] > nums[high]`, set `low = middle + 1`; otherwise set `high = middle`.
3. Return `nums[low]`.

### Correctness

Invariant: the minimum's index lies in `[low, high]`, and `nums[low..high]` is a rotated increasing sequence. Initially true. If `nums[middle] > nums[high]`, the sequence descends somewhere in `(middle, high]`; the minimum is the element right after the single descent, so it is after `middle`. If `nums[middle] < nums[high]` (values are distinct, and `middle < high` because the midpoint rounds down), then `nums[middle..high]` contains no descent and its smallest element is `nums[middle]`, so the minimum's index is at most `middle`. The range strictly shrinks each iteration and stops at a single index, which by the invariant is the minimum.

### Complexity

- Time: O(log n) — the range `high - low` halves every iteration, so there are at most about log2(n) iterations.
- Space: O(1) — two indices and a midpoint.

### Trade-offs

It is short, has no special case for the unrotated array, and is the building block of `search-rotated-array` (the pivot search there is exactly this loop). It relies on distinct values; with duplicates, `nums[middle] == nums[high]` is ambiguous and the usual fix (`high -= 1`) degrades the worst case to O(n).

### Pitfalls and edge cases

- Compare with `nums[high]`, not `nums[low]`. Comparing with the left end fails on an unrotated array: `nums[middle] > nums[low]` holds everywhere, which would push the search to the right, away from the minimum at index 0.
- Use `high = middle`, not `middle - 1`: `middle` itself may be the minimum.
- Loop while `low < high`, not `<=`; with `high = middle` a `<=` condition never terminates once `low == high`.

### Language notes

- Kotlin: `nums.lastIndex` is `nums.size - 1`; `ushr 1` is the unsigned shift that floors the midpoint.
- TypeScript and Java: `>>> 1` does the same. In Python `//` is enough because integers do not overflow.
- Go: the midpoint is `low + (high-low)/2`; `high = middle` and `low = middle + 1` keep the range non-empty.
- Rust: the indexes can be `usize`: `high = middle` never subtracts, and `nums.len() - 1` is safe because the array is not empty.
