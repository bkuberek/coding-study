# Remove Nth Node From End

## Statement

You get the head of a singly linked list and a number `n`. Count positions from the back of the list, so that the tail is position 1, the node before it is position 2, and so on. Remove the node at position `n` and return the head of the shortened list.

Removing a node means relinking its predecessor to its successor; the other nodes keep their order. If `n` equals the length of the list, the node to remove is the head itself, so the returned head changes.

Reference: this is our own wording of LeetCode problem 19, [Remove Nth Node From End of List](https://leetcode.com/problems/remove-nth-node-from-end-of-list/).

## Input

- `head`: the first node of the list, written as the array of its values from head to tail. The list has at least one node.
- `n`: the position, counted from the end starting at 1, of the node to remove.

## Output

The head of the list after the removal, written as its values from head to tail. Removing the only node gives the empty list `[]`.

## Examples

### Example 1

<!-- case: ex1 -->

Counting from the back, 7 is position 1 and 3 is position 2, so 3 is removed and 9 now links directly to 7.

### Example 2

<!-- case: ex2 -->

The list has a single node, which is position 1 from the end. Removing it leaves an empty list.

## Constraints

- The list has `L` nodes, with `1 <= L <= 10^5`.
- `1 <= n <= L`.
- `-10^4 <= node value <= 10^4`; values may repeat.

## Follow-ups

- Can you do it in a single pass over the list, without first counting its length?
- How does a placeholder node in front of the head remove the special case of deleting the head?
- How would you find the middle node of a list in one pass, using the same kind of trick?

## Hints

### Hint 1

Position `n` from the end is position `L - n + 1` from the front. If you knew `L`, you could walk to the node before it.

### Hint 2

To delete a node in a singly linked list you need its predecessor. A dummy node placed before the head gives even the head a predecessor.

### Hint 3

Start two pointers at the dummy and move the first one `n + 1` nodes ahead. Then move both together until the first one runs off the end: the second one is now just before the node to delete.
