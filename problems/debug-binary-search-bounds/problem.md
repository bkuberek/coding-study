# Debug: Binary Search Bounds

## Statement

The function `search` you start from is supposed to find `target` in `nums`, an array of distinct integers sorted in ascending order. It returns the index of `target`, or `-1` when `target` is not in the array. It must stay a binary search: O(log n) comparisons, so replacing it with a linear scan is not a fix.

The code passes most tests and fails some. Find the input that breaks it, explain why, and fix it.

### Bug report

> **Title:** Release lookup cannot find the newest build
>
> The release service keeps its build numbers in a sorted array and calls `search` to find a build's position. Lookups for older builds work. Looking up the most recent build returns `-1`, and on a fresh service that holds exactly one build, that build is never found. Someone tried a one-character patch to the loop condition; it was rolled back within the hour because lookups for builds that do not exist started hanging their request threads.

## Input

- `nums`: distinct integers in strictly ascending order (possibly empty)
- `target`: the value to look for

## Output

The index `i` with `nums[i] == target`, or `-1` when no element equals `target`.

## Examples

### Example 1

<!-- case: ex1 -->

12 sits at index 3. The buggy code already gets this one right: the search hits 12 on its first midpoint.

### Example 2

<!-- case: ex2 -->

7 falls between 5 and 8, so the answer is `-1`. This case also passes as shipped, but it is the kind of lookup that hung after the rolled-back patch.

## Constraints

- `0 <= nums.length <= 10^5`
- `-2^31 <= nums[i], target <= 2^31 - 1`
- `nums` is strictly increasing.
- The fix keeps O(log n) time and O(1) extra space.

## Follow-ups

- Rewrite the search on a half-open interval `[lo, hi)`. Which three lines change?
- Return the insertion point (the index where `target` would go) instead of `-1`.
- Why can `(lo + hi) / 2` overflow in Java for very large arrays, and how do you compute the midpoint safely?

## Hints

### Hint 1

Reproduce before you theorize. Try every target position in arrays of length 1, 2 and 3. Which positions fail?

### Hint 2

Trace `lo`, `hi` and `mid` by hand for `nums = [7]`, `target = 7`. Does the loop body run even once?

### Hint 3

The code starts with `hi = nums.length - 1`, so `[lo, hi]` is meant to include both ends. When `lo == hi` there is still one candidate. Which loop condition still checks it?

### Hint 4

If you only change the loop condition, look at `hi = mid`. When `lo == hi` and `nums[mid] > target`, does the interval get any smaller?
