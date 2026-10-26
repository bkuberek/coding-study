# Merge K Sorted Lists

## Statement

You get an array of `k` singly linked lists, each sorted in non-decreasing order. Combine all of their nodes into a single sorted list and return its head.

With two lists, you compare their two front values and take the smaller one. With `k` lists the same idea works, but comparing all `k` fronts at every step is slow when `k` is large. The challenge is to keep the cost per node close to `log k` instead of `k`.

Reference: this is our own wording of LeetCode problem 23, [Merge k Sorted Lists](https://leetcode.com/problems/merge-k-sorted-lists/).

## Input

- `lists`: an array of `k` list heads. Each list is written as the array of its values from head to tail, and any of them may be empty (`[]`). The array itself may be empty.

## Output

The head of the merged list, written as its values from head to tail. It holds every node of every input list, in non-decreasing order.

## Examples

### Example 1

<!-- case: ex1 -->

The three fronts are 2, 1 and 3, so 1 comes first. Then 2, 3 and 4 follow, and so on; each step takes the smallest value among the current fronts. All eight nodes end up in one sorted list.

### Example 2

<!-- case: ex2 -->

Empty lists contribute nothing. Only the middle list has a node, so the result is that single node.

## Constraints

- `0 <= k <= 10^4`
- Each list has between `0` and `500` nodes, and all lists together have at most `10^4` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- Every list is sorted in non-decreasing order.

## Follow-ups

- Merging the lists into the result one after another is correct. How much work does it do when there are many short lists?
- Which data structure gives you the smallest of `k` values quickly, while the values keep changing?
- Can you reach the same O(N log k) bound with no extra data structure, using only the two-list merge?

## Hints

### Hint 1

Let `N` be the total number of nodes. The next node of the result is always the smallest of the `k` current fronts.

### Hint 2

Keep the current fronts in a min-heap. Pop the smallest, append it to the result, and push its successor if it has one: every node enters and leaves the heap once, at O(log k) each.

### Hint 3

Alternatively, merge the lists in pairs (first with second, third with fourth, ...), then merge the results in pairs again. After about `log2 k` rounds one list remains, and each round touches every node once.
