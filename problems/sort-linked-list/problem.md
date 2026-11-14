# Sort a Linked List

## Statement

You get the head of a singly linked list of integers. Sort the list in non-decreasing order and return the head of the sorted list.

Arrays sort well because any element can be reached in O(1). A linked list offers none of that: reaching the middle takes a walk, and there is no going back. The challenge is to sort in O(n log n) time anyway, ideally relinking the nodes you were given rather than copying their values into an array.

Reference: this is our own wording of LeetCode problem 148, [Sort List](https://leetcode.com/problems/sort-list/).

## Input

- `head`: the first node of the list, or null for an empty list, written as the array of its values from head to tail.

## Output

The head of the sorted list, written as its values from head to tail. Equal values may appear in any relative order (they are indistinguishable in the output).

## Examples

### Example 1

<!-- case: ex1 -->

The five values come out in increasing order. A merge sort would split them into `5, 2, 8` and `1, 9`, sort each part, and merge `2, 5, 8` with `1, 9`.

### Example 2

<!-- case: ex2 -->

Duplicates are kept: both 3s appear in the result, next to each other at the end.

## Constraints

- The list has between `0` and `5 * 10^4` nodes.
- `-10^5 <= node value <= 10^5`; values may repeat.

## Follow-ups

- Insertion sort is natural for lists but quadratic. Which O(n log n) sort suits a linked list best, and why not quicksort or heapsort?
- Can you sort in O(n log n) time with only O(1) extra memory, without recursion?
- Merging is the heart of the solution. Could you reuse your answer to merging two sorted lists?

## Hints

### Hint 1

Merging two sorted lists takes linear time and no extra memory. What sort is built entirely out of merges?

### Hint 2

To split a list in half, use a slow pointer and a fast pointer: when the fast one reaches the end, the slow one is at the middle. Cut the list there, sort both halves, and merge them.

### Hint 3

Recursion costs O(log n) stack. To avoid it, work bottom-up: merge neighbouring runs of length 1, then of length 2, then 4, and so on, until one run covers the list.
