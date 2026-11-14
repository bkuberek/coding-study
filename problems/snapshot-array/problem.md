# Snapshot Array

## Statement

Design an array of `length` integers, all 0 at first, that can take snapshots.

- `set(index, value)` writes `value` at position `index`.
- `snap()` takes a snapshot of the whole array and returns its id: the first snapshot is 0, the next one is 1, and so on.
- `get(index, snapId)` returns the value that position `index` held at the moment snapshot `snapId` was taken.

Writes made after a snapshot never change what that snapshot holds.

Reference: this is our own wording of LeetCode problem 1146, [Snapshot Array](https://leetcode.com/problems/snapshot-array/).

## Input

- Constructor: `length`, the number of positions
- `set`: `index` and `value`
- `get`: `index` and `snapId`, where `snapId` names a snapshot that was already taken

## Output

`set` returns nothing. `snap` returns the id of the new snapshot. `get` returns the stored value, which is 0 for a position that was never written before that snapshot.

## Examples

### Example 1

<!-- case: ex1 -->

Positions 1 and 2 hold 7 and 3 when snapshot 0 is taken, so snapshot 0 keeps them even after position 1 becomes 9. Snapshot 1, taken later, sees the 9.

### Example 2

<!-- case: ex2 -->

Snapshots 0 and 1 are taken before anything is written, so position 0 reads 0 in both, even after 4 is written. Snapshot 2 sees the 4.

## Constraints

- `1 <= length <= 5 * 10^4`
- `0 <= index < length`
- `0 <= value <= 10^9`
- `0 <= snapId <` the number of `snap` calls made so far
- At most `5 * 10^4` calls in total after the constructor

## Follow-ups

- What does copying the whole array at every snapshot cost in time and in memory?
- If `snap` were called far more often than `set`, what would your design store per snapshot?

## Hints

### Hint 1

Store only what changes, not whole copies of the array.

### Hint 2

For each position keep the list of `(snapshot id, value)` pairs at which it changed. The ids in each list only grow.

### Hint 3

`get` looks for the last change whose snapshot id is at most `snapId`, which is a binary search. Several writes before the same snapshot only need the last one.
