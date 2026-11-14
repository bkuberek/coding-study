# Find a Peak Element

## Statement

An index `i` of an integer array `nums` is a peak when `nums[i]` is strictly greater than each of its neighbors. Positions outside the array count as lower than every value, so the first element only has to beat the second, the last element only has to beat the one before it, and in a one-element array that element is a peak.

No two adjacent elements of `nums` are equal, which guarantees that at least one peak exists. Return the index of any peak. The array is not sorted, yet a logarithmic number of steps is enough.

Reference: this is our own wording of LeetCode problem 162, [Find Peak Element](https://leetcode.com/problems/find-peak-element/).

## Input

- `nums`: an integer array in which neighboring values always differ

## Output

An index `i` such that `nums[i] > nums[i - 1]` (or `i == 0`) and `nums[i] > nums[i + 1]` (or `i == nums.length - 1`). When several peaks exist, any one of them is accepted; the expected value shown for a test is just one valid answer.

## Examples

### Example 1

<!-- case: ex1 -->

Index 1 (value 5) beats both 1 and 2, and index 3 (value 8) beats both 2 and 3, so both are peaks. Returning 1 or 3 passes; the test shows 1.

### Example 2

<!-- case: ex2 -->

The values only rise, so no inner element beats its right neighbor. The last element, 9, has only one real neighbor and beats it, so index 3 is the only peak.

## Constraints

- `1 <= nums.length <= 10^5`
- `-2^31 <= nums[i] <= 2^31 - 1`
- `nums[i] != nums[i + 1]` for every valid `i`.

## Follow-ups

- Why does a peak always exist when neighbors differ? Can you turn that argument into an algorithm?
- What goes wrong if adjacent elements may be equal?
- How would you find a peak in a two-dimensional grid, where a peak beats its four neighbors?

## Hints

### Hint 1

Pick any index and look at its right neighbor. If the neighbor is larger, keep walking uphill to the right: why must you reach a peak before falling off the end?

### Hint 2

That argument does not care how far right the peak is, only that one exists in that direction. So you can discard the whole other side.

### Hint 3

Compare `nums[middle]` with `nums[middle + 1]`. If the right one is larger, a peak lies right of `middle`; otherwise `middle` itself or something to its left is a peak.
