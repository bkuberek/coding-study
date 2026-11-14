# Linked List Cycle

## Statement

You get the head of a singly linked list. In a healthy list, following `next` links from the head eventually reaches a node whose `next` is null. In a broken one, some node's `next` points back at a node earlier in the list (or at itself), so the walk goes around a loop forever. Decide which kind of list you have: return `true` if following the links from the head never ends, and `false` otherwise.

Your function only receives the head node. It is not told the length of the list or where a loop starts, and node values say nothing about identity: different nodes may hold the same value.

Reference: this is our own wording of LeetCode problem 141, [Linked List Cycle](https://leetcode.com/problems/linked-list-cycle/).

## Input

- `head`: the first node of the list, or null for an empty list.

In the tests, a list without a loop is written as the array of its values, for example `[2, 5, 8]`. A list with a loop is written as `{"values": [...], "cycle_at": k}`: the nodes hold `values` in order, and the last node links back to the node at index `k` (0-based) instead of to null. Your code never sees `cycle_at`; it only sees the linked nodes.

## Output

`true` if the list contains a loop, `false` if it ends.

## Examples

### Example 1

<!-- case: ex1 -->

The nodes are `4 -> 7 -> 1 -> 9`, and the last node, 9, links back to index 1, the node holding 7. A walk from the head visits 4, 7, 1, 9, 7, 1, 9, ... and never ends.

### Example 2

<!-- case: ex2 -->

The last node, 8, links to null, so a walk from the head stops after three nodes.

## Constraints

- The list has between `0` and `10^5` nodes.
- `-10^5 <= node value <= 10^5`; values may repeat.
- If there is a loop, `0 <= cycle_at <` the number of nodes.

## Follow-ups

- Can you solve it with a constant amount of extra memory, without modifying the list?
- If there is a loop, how would you find the node where it starts?
- How would you compute the length of the loop?

## Hints

### Hint 1

Walking the list and stopping when you reach null works for healthy lists. What could you remember along the way to notice that you are going around a loop?

### Hint 2

Remembering every node you have visited costs memory proportional to the list. Think of two runners on a circular track, one faster than the other.

### Hint 3

Move one pointer one node per step and another two nodes per step. If the fast one reaches null there is no loop; if there is one, the fast pointer catches up with the slow one from behind.
