# Range Sum Query With Updates

## Statement

An array of integers keeps changing, one position at a time, while range totals are asked in between. Build a class that supports both operations quickly: overwriting a single value, and returning the sum of the values between two positions.

Implement the class `NumArray`:

- `NumArray(nums)` stores the initial array.
- `update(index, value)` sets `nums[index]` to `value`.
- `sumRange(left, right)` returns `nums[left] + ... + nums[right]` for the current values, both ends included.

Reference: this is our own wording of LeetCode problem 307, [Range Sum Query - Mutable](https://leetcode.com/problems/range-sum-query-mutable/).

## Input

- Constructor: `nums`, the initial array.
- `update(index, value)`: the position to overwrite, `0 <= index < nums.length`, and its new value.
- `sumRange(left, right)`: the first and last position of the range, `0 <= left <= right < nums.length`.

Each test is a sequence of calls: the constructor first, then `update` and `sumRange` calls in order.

## Output

- `sumRange` returns the current sum of the range as a 64-bit integer (`long`).
- `update` returns nothing.

The expected output lists one result per call, with `null` for the constructor and every `update`.

## Examples

### Example 1

<!-- case: ex1 -->

At first positions 1 to 3 hold 2, -4 and 6, which add up to 4. After position 2 becomes 5, the same range adds up to 2 + 5 + 6 = 13. The whole array then adds up to 1 + 2 + 5 + 6 + 3 = 17.

### Example 2

<!-- case: ex2 -->

Setting position 1 to 7, the value it already holds, leaves the total at 21. Position 0 is then overwritten twice; only the last value counts, so positions 0 to 1 add up to -3 + 7 = 4.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^5 <= nums[i], value <= 10^5`
- `0 <= index < nums.length` and `0 <= left <= right < nums.length`
- At most `10^5` calls to `update` and `sumRange` in total.
- A range sum can exceed the 32-bit range, so return it as a `long`.

## Follow-ups

- Prefix sums answer a query in O(1), but an update costs O(n). Storing the plain array makes updates O(1) and queries O(n). Can both be O(log n)?
- How would you also support adding a value to every element of a range?
- What changes for a two-dimensional grid?

## Hints

### Hint 1

Split the array into blocks whose sums you keep. A query combines a few whole blocks; an update changes the blocks that contain the position.

### Hint 2

Use blocks of power-of-two sizes arranged as a tree: each position belongs to O(log n) blocks, and every range is a union of O(log n) blocks.

### Hint 3

A Fenwick tree stores, at index `i` (1-based), the sum of the `i & -i` values ending at `i`. Walking `i -= i & -i` gives a prefix sum; walking `i += i & -i` updates every block that contains a position.
