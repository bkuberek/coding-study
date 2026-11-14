# Reverse Linked List

## Statement

You get the head of a singly linked list. Turn the list around so that the last node comes first, the second-to-last comes second, and so on, and return the head of the turned-around list.

A singly linked list only knows how to go forward: each node holds a value and a link to the next node, and the last node links to nothing. After the reversal every link must point the other way. You may rewire the given nodes or change their values; either produces the required sequence.

Reference: this is our own wording of LeetCode problem 206, [Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/).

## Input

- `head`: the first node of the list, or null for an empty list. A list is written as the array of its values from head to tail; `[]` is the empty list.

## Output

The head of the reversed list, written the same way: its values read from the new head to the new tail. An empty list stays empty.

## Examples

### Example 1

<!-- case: ex1 -->

The list `3 -> 8 -> 1 -> 6` becomes `6 -> 1 -> 8 -> 3`. Node 6 used to be the tail and is now the head; node 3 used to be the head and now links to nothing.

### Example 2

<!-- case: ex2 -->

With two nodes, reversing swaps them: the second node's link now points back at the first, and the first node's link is cleared.

## Constraints

- The list has between `0` and `3000` nodes.
- `-5000 <= node value <= 5000`; values may repeat.

## Follow-ups

- Can you reverse the list using only a constant amount of extra memory?
- Write it both iteratively and recursively. What does the recursive version cost in memory, and what would happen on a list of a million nodes?
- How would you reverse only the nodes between positions `left` and `right`, leaving the rest in place?

## Hints

### Hint 1

Walking the list once and remembering every value would let you write them back in the opposite order. Can you avoid the extra array?

### Hint 2

Visit the nodes in order and point each one's link at the node before it. Which node do you need to remember before you overwrite a link?

### Hint 3

Keep two references, `previous` (initially null) and `current` (initially the head). Each step saves `current.next`, points `current.next` at `previous`, and moves both references one node forward.
