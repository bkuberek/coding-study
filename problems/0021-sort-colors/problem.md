# Sort Colors

## Statement

An array `nums` holds a row of tokens, each painted one of three colors, encoded as `0`, `1` and `2`. Rearrange the tokens in place so that all `0`s come first, then all `1`s, then all `2`s.

Do it without a library sort and without allocating another array: the function returns nothing, and `nums` as it stands after the call is the answer.

Reference: this is our own wording of LeetCode problem 75, [Sort Colors](https://leetcode.com/problems/sort-colors/).

## Input

- `nums`: the colors, each `0`, `1` or `2`; it is modified in place

## Output

Nothing is returned. After the call, `nums` holds the same multiset of colors in non-decreasing order.

## Examples

### Example 1

<!-- case: ex1 -->

There are two tokens of each color, so the result is two `0`s, two `1`s and two `2`s.

### Example 2

<!-- case: ex2 -->

A color may be missing entirely. Here there are no `0`s, so the `1`s start at position 0.

## Constraints

- `1 <= nums.length <= 10^5`
- `nums[i]` is `0`, `1` or `2`.

## Follow-ups

- Counting the colors and rewriting the array takes two passes. Can you sort in a single pass with O(1) extra memory?
- How would your one-pass idea change for four colors? For `k` colors?
- If each token carried extra data (so you could not just overwrite colors), which approach would still work?

## Hints

### Hint 1

With only three possible values, you can count how often each appears and then write the answer directly.

### Hint 2

For a single pass, keep three regions: a block of `0`s at the front, a block of `2`s at the back, and the `1`s between them. Everything else is still unknown.

### Hint 3

Scan the unknown part from the left. A `0` swaps to the end of the front block, a `2` swaps to the start of the back block, and a `1` stays. After a swap with the back, the value you received is still unknown.
