# Search Insert Position: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| count-smaller | brute | O(n) | O(1) | the data is unsorted, or as a correctness oracle |
| lower-bound | optimal | O(log n) | O(1) | default answer |

## Approach: count-smaller (Count the values smaller than the target)

### Intuition

In increasing order, `target` goes right after every value smaller than it. So the insertion index is simply how many values are smaller, and that is also where `target` already sits when it is present.

### Algorithm

1. Start a counter at 0.
2. For each value in `nums`, increase the counter if the value is less than `target`.
3. Return the counter.

### Correctness

The values smaller than `target` form a prefix of the sorted array, since the array is increasing. Their count is therefore the index of the first value that is not smaller than `target`. If `target` is present, that value is `target` itself (distinct values), and if it is absent, inserting at that index keeps the order.

### Complexity

- Time: O(n) — one pass over the array, whatever the position of the target.
- Space: O(1) — a single counter.

### Trade-offs

It does not even need the array to be sorted for the count to be meaningful, but it ignores the order and reads every value. At n = 10^5 that is still fast, but it is the answer an interviewer expects you to improve on.

### Pitfalls and edge cases

- Use `<`, not `<=`: with `<=` a present target lands one position too far.
- A target below every value gives 0, and a target above every value gives `nums.length`.

### Language notes

- Python: `sum(1 for value in nums if value < target)`.
- Kotlin: `nums.count { it < target }`.
- Java and TypeScript: a plain loop with a counter.

## Approach: lower-bound (Binary search for the first value not below the target)

### Intuition

Along the array, the predicate `nums[i] >= target` is false for a while and then true. The answer is the first index where it turns true, or `nums.length` if it never does. A binary search finds such a boundary in logarithmic time.

### Algorithm

1. Set `low = 0` and `high = nums.length`.
2. While `low < high`: take `middle = (low + high) / 2`. If `nums[middle] < target`, set `low = middle + 1`; otherwise set `high = middle`.
3. Return `low`.

### Correctness

Invariant: every index below `low` holds a value less than `target`, and every index from `high` on holds a value that is at least `target` (the position `nums.length` counts as such by convention). Initially both ranges are empty. Each step keeps the invariant and shrinks `high - low`, since `middle` is strictly below `high` and `middle + 1` is above `low`. When `low == high`, the two sides meet exactly at the first value that is not below `target`.

### Complexity

- Time: O(log n) — the range halves at each step, so about log2(n) + 1 steps.
- Space: O(1) — two indices and the middle.

### Trade-offs

The half-open form never needs a separate "not found" branch and gives the insertion point directly. Python has `bisect.bisect_left` and Java and Kotlin have `binarySearch`, but those report a missing value differently, which is why the loop is written out.

### Pitfalls and edge cases

- Start with `high = nums.length`, not `nums.length - 1`: the answer can be past the end.
- Set `high = middle`, not `middle - 1`: `middle` itself may be the answer.
- Use `<` in the comparison; a present target must stay inside the range.

### Language notes

- Python: `bisect.bisect_left(nums, target)` is the library one-liner for exactly this; the reference writes the loop.
- Java: `Arrays.binarySearch` returns `-(insertion point) - 1` when the value is absent, so a decoding step is needed.
- Kotlin: `nums.binarySearch(target)` has the same encoding.
- TypeScript: there is no library search, and `(low + high) >>> 1` is the usual middle; Java and Kotlin use the overflow-safe `low + (high - low) / 2`.
