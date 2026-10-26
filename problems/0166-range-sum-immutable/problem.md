# Range Sum Query

## Statement

An array of integers is fixed once and then asked many questions of the same kind: what is the total of the values between two positions? Build a class that answers each question quickly, however many arrive.

Implement the class `NumArray`:

- `NumArray(nums)` stores the array. It never changes afterwards.
- `sumRange(left, right)` returns `nums[left] + nums[left + 1] + ... + nums[right]`, the sum of the values at positions `left` to `right`, both included.

Reference: this is our own wording of LeetCode problem 303, [Range Sum Query - Immutable](https://leetcode.com/problems/range-sum-query-immutable/).

## Input

- Constructor: `nums`, the array to query.
- `sumRange(left, right)`: the first and last position of the range, `0 <= left <= right < nums.length`.

Each test is a sequence of calls: the constructor first, then `sumRange` calls in order.

## Output

- `sumRange` returns the sum of the range as a 64-bit integer (`long`).

The expected output lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

Positions 0 to 2 hold 3, -1 and 4, which add up to 6. Positions 2 to 5 hold 4, 1, -5 and 9, which add up to 9. A range of one position returns that value, here -5.

### Example 2

<!-- case: ex2 -->

The same range may be asked more than once and must give the same answer every time; the whole array adds up to 20.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^5 <= nums[i] <= 10^5`
- `0 <= left <= right < nums.length`
- At most `10^5` calls to `sumRange`.
- A range sum can exceed the 32-bit range (up to `10^10` in absolute value), so return it as a `long`.

## Follow-ups

- Adding up the range on every call costs O(n) per query. Can each query cost O(1) after some preparation?
- What if `nums` could also change between queries? (See Range Sum Query With Updates.)
- How would you answer the same question for rectangles in a matrix? (See Range Sum Query 2D.)

## Hints

### Hint 1

The array never changes, so any work you do in the constructor is paid only once.

### Hint 2

Suppose you knew, for every position `i`, the total of everything before it. How does the sum from `left` to `right` relate to two of those totals?

### Hint 3

Store `prefix[i] = nums[0] + ... + nums[i - 1]`, with `prefix[0] = 0`. Then the answer is `prefix[right + 1] - prefix[left]`.
