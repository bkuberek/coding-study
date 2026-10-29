# Find a Peak Element: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| first-descent | brute | O(n) | O(1) | the array is tiny, or as a correctness oracle |
| climb-the-slope | optimal | O(log n) | O(1) | default answer |

Several answers can be valid, so tests use a checker that accepts any peak.

## Approach: first-descent (Scan for the first descent)

### Intuition

Walk from the left while the values rise. The first time the next value is smaller, the current element is higher than the one after it, and it is also higher than the one before it because the values were rising until here. If the values never fall, the last element is a peak.

### Algorithm

1. For each index `i` from 0 to n - 2, if `nums[i] > nums[i + 1]`, return `i`.
2. Return `n - 1`.

### Correctness

If the loop returns `i`, then `nums[0] < nums[1] < ... < nums[i]` (no earlier descent, and neighbors differ), so `nums[i]` beats its left neighbor, and it beats its right neighbor by the test. If the loop finishes, the whole array increases and the last element beats its only neighbor. A one-element array skips the loop and returns 0.

### Complexity

- Time: O(n) — up to n - 1 comparisons. The generator puts the first peak between n/2 and n - 1, so at least n/2 comparisons happen at every seed.
- Space: O(1) — one index.

### Trade-offs

It is simple and always returns the leftmost peak, which makes it a good oracle. Its cost depends on where that first peak is: a long climb makes it linear, which is exactly what the binary search avoids.

### Pitfalls and edge cases

- Comparing with both neighbors explicitly is unnecessary here, but if you do, positions outside the array must count as lower than any value. Using `Integer.MIN_VALUE` (or `-2^31`) as the outside value is wrong, because elements may equal it: `[-2147483648]` has a peak at 0, and `-2147483648 > -2147483648` is false. Compare indices, not sentinel values.
- The loop stops at `n - 2` so that `nums[i + 1]` stays in bounds.

### Language notes

- Kotlin: `0 until nums.lastIndex` is the half-open range `0..n-2`, empty for a single element.
- Python: `range(len(nums) - 1)` is empty for one element, which falls through to `len(nums) - 1 == 0`.
- Go: the loop condition `index < len(nums)-1` is false from the start for a single element, which falls through to `len(nums) - 1 == 0`.
- Rust: `nums.windows(2).position(|pair| pair[0] > pair[1])` visits each adjacent pair and returns the index of the first descent; a single element has no windows, so `unwrap_or(nums.len() - 1)` supplies the answer.

## Approach: climb-the-slope (Binary search toward the rising neighbor)

### Intuition

Stand at `middle` and look right. If `nums[middle + 1]` is larger, keep walking uphill to the right: the values cannot rise forever, because the array ends and the outside counts as lower, so a peak must exist to the right of `middle`. If `nums[middle + 1]` is smaller, walking uphill to the left from `middle` (or staying put) must likewise end at a peak at or left of `middle`. Each comparison therefore throws away half of the range while keeping a guaranteed peak inside it.

### Algorithm

1. Set `low = 0`, `high = n - 1`.
2. While `low < high`:
   1. Let `middle = (low + high) / 2`, rounded down, so `middle + 1 <= high`.
   2. If `nums[middle] < nums[middle + 1]`, set `low = middle + 1`; otherwise set `high = middle`.
3. Return `low`.

### Correctness

Invariant: the range `[low, high]` contains a peak of the whole array, and if `low > 0` then `nums[low - 1] < nums[low]`, and if `high < n - 1` then `nums[high] > nums[high + 1]`. In other words, the range is entered uphill from both outside ends. Initially both conditions are vacuous. If `nums[middle] < nums[middle + 1]`, setting `low = middle + 1` keeps the left condition; otherwise (`nums[middle] > nums[middle + 1]`, since neighbors differ) setting `high = middle` keeps the right one. A range entered uphill from both ends always contains a peak: its maximum element beats its neighbors inside the range, and the boundary conditions make it beat the neighbors just outside. When `low == high`, that single element is the peak.

### Complexity

- Time: O(log n) — the range halves every iteration.
- Space: O(1) — two indices and a midpoint.

### Trade-offs

It is the expected answer and shows that binary search does not need a sorted array, only a test that tells you which half is guaranteed to hold an answer. It returns some peak, not a specific one, so tests need a checker. If the problem asked for the highest peak, no sublinear method exists in general.

### Pitfalls and edge cases

- Round the midpoint down so that `middle + 1` exists; with `low < high`, `middle` is at most `high - 1`.
- Use `high = middle`, not `middle - 1`: `middle` may be the peak.
- Equal neighbors break the argument (a flat stretch tells you nothing about which way is uphill); the constraints forbid them.
- No sentinel values are needed, so elements equal to `-2^31` cause no trouble.

### Language notes

- All four languages compare `int` values directly; there is no arithmetic on values, so overflow cannot occur even at the extremes of the 32-bit range.
- Kotlin: `nums.lastIndex` is `n - 1`; `ushr 1` floors the midpoint. Java and TypeScript use `>>> 1`; Python uses `//`.
- Go: the midpoint is `low + (high-low)/2`, and `nums[middle+1]` is in range because `low < high` implies `middle < high`.
- Rust: the indexes can stay `usize`: `high = middle` and `low = middle + 1` never subtract, and `nums.len() - 1` is safe for a non-empty array.
