# Reorder List

## Statement

You get the head of a singly linked list with nodes `L0, L1, ..., Ln-1` in that order. Rearrange the nodes so that the list alternates between the front and the back of the original order:

`L0, Ln-1, L1, Ln-2, L2, Ln-3, ...`

The first node stays first, the last node becomes second, the second node becomes third, the second-to-last node becomes fourth, and so on until every node has been placed. Do this by relinking the existing nodes in place; do not change the values stored in them. The function returns nothing: the tests read the list from the original head after your function returns.

Reference: this is our own wording of LeetCode problem 143, [Reorder List](https://leetcode.com/problems/reorder-list/).

## Input

- `head`: the first node of the list, written as the array of its values from head to tail. The list has at least one node.

## Output

Nothing is returned. The checked result is the list read from `head` after the call, as an array of values.

## Examples

### Example 1

<!-- case: ex1 -->

The five nodes are taken alternately from the front and the back: 10 (first), 50 (last), 20 (second), 40 (second-to-last), and finally 30, the middle node, which ends the list.

### Example 2

<!-- case: ex2 -->

With an even number of nodes, the last two placed are the two middle nodes, 3 and 9, in their original order.

## Constraints

- The list has between `1` and `5 * 10^4` nodes.
- `-1000 <= node value <= 1000`; values may repeat.
- Relink the nodes; do not overwrite their values.

## Follow-ups

- Moving the tail forward one step at a time is quadratic. Can you do it in linear time?
- Can you do it in linear time with only a constant amount of extra memory?
- The optimal answer combines three classic list routines. Which ones, and could you write each from memory?

## Hints

### Hint 1

Singly linked lists cannot walk backwards. If you could index the nodes by position, which pairs of indexes would you link?

### Hint 2

The back half of the list is consumed from its end, in reverse order. What if you reversed the back half first?

### Hint 3

Find the middle with a slow and a fast pointer, cut the list there, reverse the second half, and then interleave the two halves one node at a time.
