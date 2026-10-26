# Reverse Nodes in K-Groups

## Statement

You get the head of a singly linked list and a positive integer `k`. Cut the list, from the head, into consecutive groups of `k` nodes and reverse the order of the nodes inside each group. If the list's length is not a multiple of `k`, the last few nodes do not form a full group: leave them exactly as they are. Return the head of the resulting list.

Rearrange the nodes themselves by relinking them; the values stored in the nodes stay with their nodes. Groups keep their relative order: only the nodes within each full group are turned around.

Reference: this is our own wording of LeetCode problem 25, [Reverse Nodes in k-Group](https://leetcode.com/problems/reverse-nodes-in-k-group/).

## Input

- `head`: the first node of the list, written as the array of its values from head to tail. The list has at least one node.
- `k`: the group size, between 1 and the length of the list.

## Output

The head of the rearranged list, written as its values from head to tail.

## Examples

### Example 1

<!-- case: ex1 -->

The seven nodes form two full groups of three, `11 12 13` and `14 15 16`, and a leftover single node `17`. Each full group is reversed and the leftover stays where it is.

### Example 2

<!-- case: ex2 -->

With `k = 2`, neighbouring nodes swap places: the length is a multiple of 2, so there is no leftover.

## Constraints

- The list has between `1` and `10^5` nodes.
- `1 <= k <=` the number of nodes.
- `-1000 <= node value <= 1000`; values may repeat.
- Relink the nodes; do not just rewrite their values.

## Follow-ups

- Can you solve it with only a constant amount of extra memory?
- How would you do it recursively, and how deep would the recursion get for `k = 1`?
- What if the leftover nodes at the end should be reversed too?

## Hints

### Hint 1

Before reversing a group, check that it is complete: walk `k` nodes ahead and see whether you fall off the end.

### Hint 2

Reversing a group is the classic list reversal, except that the group's old first node must end up pointing at the node that follows the group, and the node before the group must end up pointing at the group's old last node.

### Hint 3

Keep a reference to the node just before the current group (start with a dummy node before the head). After reversing, the group's old first node is its new last node, which makes it the "node before" for the next group.
