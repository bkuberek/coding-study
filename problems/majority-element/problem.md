# Majority Element

## Statement

You get an integer array `nums` of length `n`. One value fills more than half of its positions: it occurs strictly more than `n / 2` times (rounded down). Find that value.

Every input is guaranteed to have such a value, so there is always exactly one answer. The other positions can hold any values, including repeated ones.

Reference: this is our own wording of LeetCode problem 169, [Majority Element](https://leetcode.com/problems/majority-element/).

## Input

- `nums`: the array to inspect; one value occurs in more than half of its positions

## Output

The value that occurs more than `n / 2` times.

## Examples

### Example 1

<!-- case: ex1 -->

There are five positions, so the answer must occur at least three times. The value 3 occurs three times; 8 and 1 occur once each.

### Example 2

<!-- case: ex2 -->

With six positions the answer needs at least four occurrences. The value 6 occurs four times. The value -4 occurs twice, which is not enough even though it is the second most common value.

## Constraints

- `1 <= nums.length <= 5 * 10^4`
- `-10^9 <= nums[i] <= 10^9`
- Some value occurs more than `nums.length / 2` times (rounded down).

## Follow-ups

- Can you find the answer in O(n) time with O(1) extra memory?
- If the input were not guaranteed to have a majority value, how would you detect that none exists?
- How would you find every value that occurs more than `n / 3` times?

## Hints

### Hint 1

Counting how often each value occurs answers the question directly. How expensive is that without extra memory, and with a hash map?

### Hint 2

If you sort the array, which position is always covered by the majority value, wherever its block of copies starts?

### Hint 3

Pair up each occurrence of the majority value with a different value and cancel both. Since the majority value fills more than half of the positions, can all of its copies be cancelled?

### Hint 4

Keep one candidate and a counter. A value equal to the candidate adds a vote, any other value removes one, and a counter at zero lets the next value become the candidate.
