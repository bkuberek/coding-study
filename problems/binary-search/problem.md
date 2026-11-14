# Binary Search

## Statement

You are given an array `nums` whose values are distinct and appear in strictly increasing order, together with a value `target`. Report where `target` sits in `nums`, or report that it is not there at all.

The array can be long, so the intended solution should not look at every element: each comparison against a middle element tells you which half of the remaining range can still contain `target`.

Reference: this is our own wording of LeetCode problem 704, [Binary Search](https://leetcode.com/problems/binary-search/).

## Input

- `nums`: distinct integers sorted from smallest to largest
- `target`: the value to locate

## Output

The index `i` with `nums[i] == target`, or `-1` when no element equals `target`. Because the values are distinct, at most one index qualifies.

## Examples

### Example 1

<!-- case: ex1 -->

The value 8 is the fourth element, so the answer is index 3. A binary search first compares 8 with the middle element 3 and discards everything up to it, then compares with 15 and discards everything from it, leaving only index 3.

### Example 2

<!-- case: ex2 -->

The value 7 would fit between 6 and 9, but it is not in the array, so the answer is `-1`.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- `nums[i] < nums[i + 1]` for every valid `i`.

## Follow-ups

- Can you answer with O(log n) comparisons instead of n?
- If `target` is absent, how would you return the index where it would have to be inserted to keep `nums` sorted?
- What changes if the values may repeat and you must return the first position of `target`?

## Hints

### Hint 1

Compare `target` with the element in the middle of the array. What do you learn about every element to its left, and every element to its right?

### Hint 2

Keep two indices that bound the part of the array where `target` could still be. Each comparison should shrink that range by about half.

### Hint 3

Decide whether your bounds are inclusive or exclusive before writing the loop, and make the loop condition and the updates agree with that choice, or the search can skip the last candidate or loop forever.
