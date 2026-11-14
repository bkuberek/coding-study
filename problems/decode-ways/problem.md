# Decode Ways

## Statement

A message made of capital letters was encoded by replacing each letter with its position in the alphabet, so `A` became `1`, `B` became `2`, and so on up to `Z`, which became `26`. The numbers were written one after another with no separators, which makes the encoding ambiguous: `"12"` can come from `AB` (1, 2) or from `L` (12).

Given the digit string `s`, count how many letter messages could have produced it. A valid reading splits `s` into pieces of one or two digits, where every piece is a number from 1 to 26 written without a leading zero. A piece such as `"0"`, `"07"` or `"30"` is not a letter.

Reference: this is our own wording of LeetCode problem 91, [Decode Ways](https://leetcode.com/problems/decode-ways/).

## Input

- `s`: the encoded digits

## Output

The number of ways to split `s` into pieces that each encode a letter; `0` if there is none.

## Examples

### Example 1

<!-- case: ex1 -->

Three readings: 1, 2, 3 (ABC), 12, 3 (LC) and 1, 23 (AW).

### Example 2

<!-- case: ex2 -->

A zero cannot stand alone, so each `0` must be paired with the digit before it: the only reading is 10, 20 (JT).

### Example 3

<!-- case: ex3 -->

The `0` would have to join the `3` before it, but 30 is not a letter, so no reading exists.

## Constraints

- `1 <= s.length <= 2000`
- `s` contains only the digits `0` to `9`, and may start with `0`.
- The number of readings of `s`, and of every prefix of `s`, fits in a 32-bit signed integer.

## Follow-ups

- How is this related to counting the ways to climb a staircase one or two steps at a time?
- Can you compute the count with constant extra memory?
- How would the count change if a `*` could stand for any digit from 1 to 9?

## Hints

### Hint 1

Look at the last piece of a reading. It is either the last digit alone or the last two digits together. Each choice is allowed only under some condition.

### Hint 2

Let `ways[i]` be the number of readings of the first `i` digits. Then `ways[i]` gets `ways[i - 1]` when digit `i - 1` is not `0`, plus `ways[i - 2]` when the two digits ending at position `i - 1` form a number from 10 to 26.

### Hint 3

Set `ways[0] = 1` for the empty prefix, and notice that each entry depends only on the two before it.
