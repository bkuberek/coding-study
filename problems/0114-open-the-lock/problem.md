# Open the Lock

## Statement

A combination lock has four wheels, each showing a digit from `0` to `9`. The lock currently shows `"0000"`. One move turns a single wheel by one notch, up or down; the wheels wrap around, so one move turns `9` into `0` and another turns `0` into `9`.

Some settings are traps: if the lock ever shows one of the strings in `deadends`, it jams for good. You want the lock to show `target`. Return the fewest moves that get there without ever showing a dead end along the way, or `-1` if that is impossible. If `"0000"` itself is a dead end, the lock is jammed from the start.

Reference: this is our own wording of LeetCode problem 752, [Open the Lock](https://leetcode.com/problems/open-the-lock/).

## Input

- `deadends`: the settings that jam the lock, each a string of four digits.
- `target`: the setting to reach, a string of four digits.

## Output

The smallest number of moves from `"0000"` to `target` that never passes through a dead end; `0` if `target` is `"0000"`; `-1` if no such sequence exists.

## Examples

### Example 1

<!-- case: ex1 -->

The four settings one move up from `"0000"` are all dead ends, so both two-move routes to `"0011"` are closed. A detour of four moves works: turn the second wheel down to `"0900"`, then reach `"0910"` and `"0911"`, and turn the second wheel back up through the wrap-around to `"0011"`.

### Example 2

<!-- case: ex2 -->

All eight settings one move away from `"0000"` are dead ends, so the first move already jams the lock and no target other than `"0000"` can be reached.

## Constraints

- `1 <= deadends.length <= 5000`
- Every dead end and `target` consist of exactly four digits.
- The dead ends are distinct, and `target` is not one of them.

## Follow-ups

- Return one shortest sequence of settings, not only its length.
- Searching from both ends at once usually explores far fewer settings. Why?
- How does the work grow with the number of wheels and the digits per wheel?

## Hints

### Hint 1

Think of each of the 10,000 settings as a node and each move as an edge. Every node has exactly eight neighbors.

### Hint 2

The fewest moves is a shortest path where every edge costs the same, so a breadth-first search from `"0000"` finds it. Treat dead ends as nodes that may never be entered.

### Hint 3

Put the dead ends in a hash set before the search, and check the start: if `"0000"` is a dead end, stop immediately.
