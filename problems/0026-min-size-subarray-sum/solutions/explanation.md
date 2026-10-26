# Minimum Size Subarray Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| prefix-binary-search | intermediate | O(n log n) | O(n) | many queries with different targets over one array |
| sliding-window | optimal | O(n) | O(1) | default answer |

All three rely on the values being positive: a longer run always has a larger sum.

## Approach: brute-force (Extend from every start until the sum is reached)

### Intuition

For each start, add elements one by one until the sum reaches `target`. That is the shortest valid run with this start, because a longer one only adds more. Keep the shortest over all starts.

### Algorithm

1. Set `best = 0` (meaning "none found yet").
2. For each `start`: set `total = 0`; for each `end` from `start`, add `nums[end]`; when `total >= target`, update `best` with `end - start + 1` if it is smaller (or the first), and stop this start.
3. Return `best`.

### Correctness

For a fixed start, the running sums strictly increase with `end`, so the first `end` where the sum reaches `target` gives the shortest valid run with that start, and no shorter one exists. Every subarray has a start, so the minimum over starts is the answer. If no start ever reaches `target`, `best` stays 0, as required.

### Complexity

- Time: O(n^2) — each start can scan to the end of the array. The generator sets the target to 10% to 30% of the total, so the scans are long at every seed.
- Space: O(1) — a few integers.

### Trade-offs

Correct and short, hence the oracle. Every start recomputes sums that the previous start already had: the window for `start + 1` is the window for `start` minus one element. The sliding window removes exactly that waste.

### Pitfalls and edge cases

- Use 0 as "not found" only if you also check it explicitly when taking the minimum, as the reference does, or start from a sentinel larger than n and map it to 0 at the end.
- "At least" means `>=`, not `>`: a run summing exactly to `target` is valid.
- The largest possible sum is 10^5 * 10^4 = 10^9, which fits a 32-bit integer.

### Language notes

- Python: two plain loops; CPython does about 10^7 simple steps per second, so n = 10^4 takes around half a second here.
- TypeScript, Java, Kotlin: the same two loops over `number[]`, `int[]` or `IntArray`, with no allocation.

## Approach: prefix-binary-search (Prefix sums with a binary search per start)

### Intuition

Let `prefix[i]` be the sum of the first `i` elements. The run `nums[start .. end-1]` has sum `prefix[end] - prefix[start]`. Because all values are positive, `prefix` is strictly increasing, so for each start the smallest `end` with `prefix[end] >= prefix[start] + target` can be found by binary search.

### Algorithm

1. Build `prefix` of length n + 1 with `prefix[0] = 0` and `prefix[i+1] = prefix[i] + nums[i]`.
2. For each `start` from 0 to n - 1:
   1. Find the smallest `end > start` with `prefix[end] >= prefix[start] + target`.
   2. If it exists (`end <= n`), update `best` with `end - start`.
3. Return `best` (0 if nothing was found).

### Correctness

`prefix[end] - prefix[start]` is the sum of `nums[start .. end-1]`, so the condition says exactly that this run reaches `target`. Since `prefix` is strictly increasing, the valid `end` values form a suffix of `start+1 .. n`, and the binary search finds its first element, the shortest valid run for this start. Taking the minimum over all starts gives the answer.

### Complexity

- Time: O(n log n) — building prefix sums is O(n), and each of the n searches is O(log n).
- Space: O(n) — the prefix array.

### Trade-offs

A useful technique in its own right: with the prefix array built once, any target can be answered in O(n log n), and it extends to other monotone conditions. For one query it is slower and uses more memory than the sliding window. It also needs positive values: with zeros the prefix array is only non-decreasing (still searchable), with negatives it is not monotone at all.

### Pitfalls and edge cases

- Search only among `end > start`, so the run is non-empty.
- The search key `prefix[start] + target` can reach 2 * 10^9, which still fits a 32-bit signed integer, but only just; a larger target range would need `long`.
- A "not found" result is position n + 1 (past the array); check for it before using the length.

### Language notes

- Python: `[0, *accumulate(nums)]` builds the prefix sums; `bisect_left(prefix, key, start + 1)` searches from `start + 1`.
- TypeScript: no built-in binary search; the reference writes a lower bound with `>>> 1` for the midpoint.
- Java: `Arrays.binarySearch(prefix, from, to, key)` returns the position when found and `-(insertionPoint) - 1` otherwise. Prefix sums are strictly increasing here, so either result gives the lower bound directly.
- Kotlin: `IntArray.binarySearch(element, fromIndex)` follows the same contract.

## Approach: sliding-window (Grow on the right and shrink on the left)

### Intuition

Keep a window `[left, right]` and its sum. Extend it on the right one element at a time. As soon as the sum reaches `target`, the window is valid; record its length and drop elements on the left while it stays valid, since each drop gives a shorter candidate. Neither edge ever moves backwards, so each element enters and leaves the window once.

### Algorithm

1. Set `best = 0`, `total = 0`, `left = 0`.
2. For each `right`: add `nums[right]` to `total`; while `total >= target`, update `best` with `right - left + 1`, subtract `nums[left]` and increase `left`.
3. Return `best`.

### Correctness

Every recorded length belongs to a window whose sum reaches `target`, so `best` is never too small. It remains to show that a shortest valid window `nums[s .. e]` is recorded. The left edge moves past a position `p` only right after recording a valid window that starts at `p` and ends at or before the current `right`. If `left` had moved past `s` before `right` reached `e`, that recorded window `nums[s .. r]` with `r < e` would be valid and shorter, a contradiction. So when `right = e`, the window `[left, e]` contains `[s, e]` and its sum reaches `target`. The inner loop then records and drops elements while the window stays valid; every window `[l, e]` with `l <= s` contains `[s, e]` and is valid, so the loop reaches `left = s` and records `e - s + 1`.

### Complexity

- Time: O(n) — `right` takes n steps and `left` at most n in total across all inner loops.
- Space: O(1) — a sum and two indices.

### Trade-offs

Linear time, constant memory, a handful of lines: the expected answer. It depends on positivity in a stronger way than the prefix approach: with negative values, dropping an element can raise the sum, and the window invariant breaks (that version needs a monotonic deque over prefix sums).

### Pitfalls and edge cases

- Shrink with `while`, not `if`: one new large element can make several left elements unnecessary, as in `[1, 1, 1, 100]` with target 100.
- Record the length before dropping the left element.
- If the loop never records anything, return 0.

### Language notes

- Python: `enumerate` gives `right` and the value together; the inner `while` runs at most n times in total.
- TypeScript: `nums[left++]` reads the value and advances the index in one expression.
- Java: same idiom; the sum stays within `int` because it never exceeds the total of the array.
- Kotlin: `nums[left++]` works as in Java; `IntArray` avoids boxing.
