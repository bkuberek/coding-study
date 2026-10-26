# Search in Rotated Sorted Array: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-scan | brute | O(n) | O(1) | the array is tiny, or as a correctness oracle |
| pivot-then-search | optimal | O(log n) | O(1) | you want two simple, well-known searches instead of one subtle one |
| one-pass | optimal | O(log n) | O(1) | default interview answer: one loop, one pass |

## Approach: linear-scan (Scan every position)

### Intuition

The rotation does not change which values are present, so comparing `target` with every element from left to right always finds it if it is there.

### Algorithm

1. For each index `i` from 0 to n - 1, if `nums[i] == target`, return `i`.
2. Return `-1`.

### Correctness

Every index is compared with `target`, so a present value is found, and an index is returned only when it holds `target`. Values are distinct, so the match is unique.

### Complexity

- Time: O(n) — one comparison per element in the worst case; the generator places a present target in the back half of the array, so at least n/2 comparisons happen at every seed.
- Space: O(1) — one loop index.

### Trade-offs

It ignores all the structure and is correct for any array, which makes it a good oracle and a poor interview answer: the whole point of the problem is to keep binary search working despite the break.

### Pitfalls and edge cases

- None specific to the rotation: it behaves the same on rotated and sorted input.
- Return `-1`, not a falsy value, when the loop finishes.

## Approach: pivot-then-search (Find the rotation point, then search one sorted run)

### Intuition

A rotated array is two increasing runs, and the second run starts at the smallest element (the pivot). The pivot can itself be found by binary search, because "is `nums[i]` at most the last element?" is false on the first run and true on the second. With the pivot known, comparing `target` with the ends of the second run says which run can contain it, and an ordinary binary search finishes the job.

### Algorithm

1. Find the pivot: `low = 0`, `high = n - 1`; while `low < high`, take `middle`; if `nums[middle] > nums[high]` the minimum is right of `middle`, so `low = middle + 1`; otherwise `high = middle`. The pivot is `low`.
2. If `nums[pivot] <= target <= nums[n - 1]`, binary search `target` in `[pivot, n - 1]`.
3. Otherwise binary search it in `[0, pivot - 1]` (an empty range when the pivot is 0).

### Correctness

Pivot search invariant: the index of the minimum lies in `[low, high]`. If `nums[middle] > nums[high]`, there is a descent between `middle` and `high`, so the minimum is after `middle`. Otherwise `nums[middle..high]` is increasing, so nothing after `middle` is smaller than `nums[middle]` and the minimum is at or before `middle`. The range shrinks every step and ends on the minimum. Then `nums[pivot..n-1]` holds exactly the values between `nums[pivot]` and `nums[n-1]`, and `nums[0..pivot-1]` holds only values larger than `nums[n-1]`; so if `target` is present it lies in the run selected in step 2 or 3, and the binary search on that sorted run finds it.

### Complexity

- Time: O(log n) — two binary searches, each at most about log2(n) + 1 iterations.
- Space: O(1) — a few indices.

### Trade-offs

Both parts are standard searches that are easy to get right and to test separately, and the pivot search is reused verbatim in `min-in-rotated-array`. It does about twice as many probes as the one-pass version, which is irrelevant in practice but may come up as a follow-up.

### Pitfalls and edge cases

- Compare `nums[middle]` with `nums[high]`, not with `nums[low]`: with no rotation, `nums[middle] > nums[low]` holds everywhere and would wrongly push `low` past the minimum at index 0.
- With pivot 0 the "first run" is empty; the range `[0, -1]` makes the second search return `-1` immediately.
- The range test in step 2 must include both ends: `target == nums[pivot]` or `target == nums[n - 1]` belongs to the second run.

### Language notes

- Kotlin: `target in nums[pivot]..nums[last]` expresses the inclusive range test directly.
- TypeScript and Java: `>>> 1` floors the midpoint of two non-negative indices without overflow; Python needs only `//`.

## Approach: one-pass (One binary search that keeps the sorted half in view)

### Intuition

Cut the current range at `middle`. One side of the cut is always sorted: if `nums[low] <= nums[middle]` the break is not in the left half, otherwise it is in the left half and the right half is sorted. A sorted half answers "could `target` be in here?" with two comparisons against its ends. If yes, search it; if no, `target` can only be in the other half.

### Algorithm

1. Set `low = 0`, `high = n - 1`.
2. While `low <= high`:
   1. Let `middle` be the midpoint. If `nums[middle] == target`, return `middle`.
   2. If `nums[low] <= nums[middle]` (left half sorted): if `nums[low] <= target < nums[middle]`, set `high = middle - 1`, else `low = middle + 1`.
   3. Otherwise (right half sorted): if `nums[middle] < target <= nums[high]`, set `low = middle + 1`, else `high = middle - 1`.
3. Return `-1`.

### Correctness

Invariant: if `target` is present, its index lies in `[low, high]`, and `nums[low..high]` is a rotated increasing sequence (a contiguous piece of one stays one). In a rotated sequence at most one adjacent pair descends. If `nums[low] <= nums[middle]`, a descent inside `[low, middle]` would make `nums[low] > nums[middle]` (values after the descent are all smaller than those before it), so the left half is sorted and contains `target` exactly when `nums[low] <= target < nums[middle]`. Otherwise the descent is in the left half, so the right half is sorted, and the symmetric test applies. Either way the half that is kept still contains `target` if it is present, and the range shrinks by at least one each iteration.

### Complexity

- Time: O(log n) — every iteration discards at least half of `[low, high]`.
- Space: O(1) — three indices.

### Trade-offs

One loop and the fewest probes, which makes it the expected answer. The price is subtlety: four comparisons with mixed strict and non-strict bounds, each of which is a classic off-by-one. If you blank on them in an interview, the pivot-then-search version is a perfectly good fallback.

### Pitfalls and edge cases

- Use `nums[low] <= nums[middle]`, not `<`: when `low == middle` (a one- or two-element range) the left "half" is the single element `nums[low]`, which is sorted.
- The bounds are asymmetric on purpose: `target < nums[middle]` and `nums[middle] < target` are strict because `middle` was already checked; the outer ends `nums[low]` and `nums[high]` are inclusive.
- Distinct values are essential. With duplicates, `nums[low] == nums[middle] == nums[high]` gives no information about which half is sorted (see the follow-up).

### Language notes

- Kotlin: the reference computes which half is sorted and whether `target` falls in it as two booleans, then keeps the left half exactly when they agree; it is the same decision table as the `if` chain in the other languages.
- All four languages compare `int` values directly; no value arithmetic happens, so overflow is impossible.
