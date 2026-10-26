# Move Zeroes

## Statement

You get an integer array `nums`. Rearrange it in place so that every non-zero value comes before every zero. The non-zero values must keep the order in which they appeared, and the number of zeros must stay the same.

Work inside `nums` itself: the function returns nothing, and the array as it stands after the call is the answer. Avoid allocating a second array of the same size.

Reference: this is our own wording of LeetCode problem 283, [Move Zeroes](https://leetcode.com/problems/move-zeroes/).

## Input

- `nums`: the array to rearrange; it is modified in place

## Output

Nothing is returned. After the call, `nums` holds its non-zero values in their original relative order, followed by all of its zeros.

## Examples

### Example 1

<!-- case: ex1 -->

The non-zero values 7, -3 and 12 move to the front in the order they appeared, and the two zeros fill the last two positions.

### Example 2

<!-- case: ex2 -->

The only non-zero value moves from the last position to the first. Both zeros end up behind it.

## Constraints

- `1 <= nums.length <= 10^5`
- `-2^31 <= nums[i] <= 2^31 - 1`

## Follow-ups

- Can you do it with O(1) extra memory?
- Can you keep the number of writes to `nums` as small as possible when there are only a few zeros?
- How would you move every value equal to some `x` to the end instead? To the front, without keeping the order of the others?

## Hints

### Hint 1

If you could use a second array, how would you fill it? Which values go in first?

### Hint 2

The final position of the k-th non-zero value is index k. Can one index remember where the next non-zero value belongs while another reads the array?

### Hint 3

A write index never overtakes the read index, so writing at it never destroys a value you have not read yet.
