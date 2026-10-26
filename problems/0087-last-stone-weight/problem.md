# Last Stone Weight

## Statement

You have a pile of stones, each with a positive integer weight. Repeatedly pick up the two heaviest stones and smash them together. If their weights are `x <= y`:

- when `x == y`, both stones are destroyed;
- when `x < y`, the lighter stone is destroyed and the heavier one survives with weight `y - x`, going back onto the pile.

Keep smashing while at least two stones are left. Return the weight of the last remaining stone, or `0` if no stone survives.

Reference: this is our own wording of LeetCode problem 1046, [Last Stone Weight](https://leetcode.com/problems/last-stone-weight/).

## Input

- `stones`: the weights of the stones in the pile, in no particular order.

## Output

The weight of the stone left at the end, or `0` when the pile ends up empty.

## Examples

### Example 1

<!-- case: ex1 -->

7 and 5 are the heaviest and leave a stone of 2. The pile is now 3, 2, 2, 2: smashing 3 and 2 leaves 1, then the two remaining 2s destroy each other, and the stone of weight 1 is the last one.

### Example 2

<!-- case: ex2 -->

Two equal stones destroy each other, so nothing is left.

## Constraints

- `1 <= stones.length <= 10^4`
- `1 <= stones[i] <= 1000`

## Follow-ups

- Sorting the pile before every smash works. How much does it cost over all rounds?
- Which data structure hands you the largest element quickly while elements keep being added?
- If the weights are small integers, can you avoid comparisons altogether?

## Hints

### Hint 1

Each round only needs the two largest weights. The rest of the pile's order does not matter.

### Hint 2

After a smash, the new stone is lighter than the heavier stone was, but it may still be heavier than many others: it has to go back to its correct place in the order.

### Hint 3

A max-heap gives the heaviest stone in O(1), removes it in O(log n), and inserts the leftover in O(log n). In languages with only a min-heap, store negated weights.
