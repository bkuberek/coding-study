# Merge Two Sorted Lists

## Statement

You get the heads of two singly linked lists, `list1` and `list2`. Each list is already sorted in non-decreasing order. Combine them into one list that holds every node of both and is still sorted, and return its head.

Think of two sorted stacks of numbered cards that you have to deal into one sorted pile. You never need to look further than the top card of each stack. You may relink the given nodes (the classic answer) or build new ones; only the resulting sequence of values is checked.

Reference: this is our own wording of LeetCode problem 21, [Merge Two Sorted Lists](https://leetcode.com/problems/merge-two-sorted-lists/).

## Input

- `list1`: the head of the first sorted list, or null when it is empty.
- `list2`: the head of the second sorted list, or null when it is empty.

A list is written as the array of its values from head to tail; `[]` is the empty list.

## Output

The head of the merged list, written as its values from head to tail. Its length is the sum of the two input lengths, and its values are in non-decreasing order.

## Examples

### Example 1

<!-- case: ex1 -->

The merge compares the two front values at every step: 1 beats 2, then 2 beats 4, then the two 4s tie (either may go first), and so on. Once the first list runs out after 9, the rest of the second list, 12, is attached as it is.

### Example 2

<!-- case: ex2 -->

When one list is empty, the merged list is simply the other one.

## Constraints

- Each list has between `0` and `3000` nodes, and the two lists together have at most `3000` nodes.
- `-5000 <= node value <= 5000`; values may repeat, within a list and across the lists.
- Both lists are sorted in non-decreasing order.

## Follow-ups

- Can you merge using only a constant amount of extra memory, by relinking the existing nodes?
- Write a recursive version. How deep does the recursion go?
- How would you merge `k` sorted lists instead of two, without comparing every front value at every step?

## Hints

### Hint 1

The smallest value of the merged list is the smaller of the two heads. After you take it, the problem is the same as before, with one node fewer.

### Hint 2

Build the result by appending one node at a time to a tail reference. A placeholder node in front of the result saves you from treating the first append as a special case.

### Hint 3

When one list runs out, the remaining nodes of the other are already sorted and all at least as large as everything merged so far: link them in one step.
