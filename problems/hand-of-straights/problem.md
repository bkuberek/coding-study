# Hand of Straights

## Statement

You hold a hand of cards, and `hand[i]` is the number written on card `i`. Decide whether the whole hand can be split into groups of exactly `groupSize` cards each, where every group is a straight: its numbers are consecutive, such as 7, 8, 9.

Every card must go into exactly one group. Cards with the same number are different cards, so a hand may contain several straights that use the same numbers.

Reference: this is our own wording of LeetCode problem 846, [Hand of Straights](https://leetcode.com/problems/hand-of-straights/).

## Input

- `hand`: the numbers on the cards, in no particular order
- `groupSize`: the number of cards in every straight

## Output

`true` if the cards can be arranged into straights of length `groupSize` with no card left over, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The nine cards form the straights 2, 3, 4 and 3, 4, 5 and 4, 5, 6.

### Example 2

<!-- case: ex2 -->

The card 3 can only start a straight, so 3, 4, 5 must be one group. That leaves 4, 6 and 7, which are not consecutive.

### Example 3

<!-- case: ex3 -->

Five cards cannot be split into groups of two.

## Constraints

- `1 <= hand.length <= 10^4`
- `0 <= hand[i] <= 10^9`
- `1 <= groupSize <= hand.length`

## Follow-ups

- Which card is forced to start a straight, and why does that make a greedy strategy safe?
- Can you avoid removing cards from a list one at a time?
- How would you also return the straights themselves?

## Hints

### Hint 1

If the number of cards is not a multiple of `groupSize`, the answer is `false`.

### Hint 2

The smallest card cannot be in the middle or at the end of a straight, so it must start one. Remove that straight and repeat.

### Hint 3

Count the cards per number and visit the numbers in increasing order. When a number still has `c` cards left, it must start `c` straights, which use `c` cards of each of the next `groupSize - 1` numbers.
