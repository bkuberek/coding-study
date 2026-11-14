# Search Insert Position

## Statement

`nums` holds distinct integers in increasing order. Return the index of `target` if it is in `nums`. Otherwise return the index at which it would have to be inserted to keep `nums` in increasing order.

Reference: this is our own wording of LeetCode problem 35, [Search Insert Position](https://leetcode.com/problems/search-insert-position/).

## Input

- `nums`: distinct integers in increasing order
- `target`: the value to look for

## Output

An index from `0` to `nums.length`.

## Examples

### Example 1

<!-- case: ex1 -->

The value 7 is at index 2.

### Example 2

<!-- case: ex2 -->

The value 9 is missing. It belongs after 7 (index 2) and before 12 (index 3), so inserting it at index 3 keeps the order.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i], target <= 10^9`
- `nums` is strictly increasing

## Follow-ups

- Can you do it in O(log n) time?
- What would you return if `nums` could hold duplicates and the target had to go before all the copies? After all of them?

## Hints

### Hint 1

Whether or not `target` is present, the answer is the number of values smaller than it.

### Hint 2

Binary search for the first position whose value is at least `target`. Keep the answer inside a range `[low, high]` that shrinks at every step, and start `high` at `nums.length`, because the answer can be past the end.
