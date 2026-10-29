# Can Attend All Meetings

## Statement

You have a list of meetings for the day. Meeting `i` runs from time `intervals[i][0]` up to, but not including, time `intervals[i][1]`. You want to attend every meeting from its start to its end, and you can walk out of a meeting that ends at time `t` straight into one that starts at time `t`.

Return `true` if no two meetings share a moment, and `false` otherwise.

Reference: this is our own wording of LeetCode problem 252, [Meeting Rooms](https://leetcode.com/problems/meeting-rooms/).

## Input

- `intervals`: the meetings as `[start, end]` pairs, in any order; the list may be empty

## Output

`true` when all the meetings can be attended, which happens exactly when no two of them overlap.

## Examples

### Example 1

<!-- case: ex1 -->

The meeting `[11, 14]` starts at 11, while `[9, 12]` is still running, and it is still running at 13 when `[13, 15]` starts, so you cannot attend everything.

### Example 2

<!-- case: ex2 -->

The meeting `[8, 10]` ends exactly when `[10, 12]` starts, which is allowed, and `[13, 14]` comes after a break, so all three fit.

## Constraints

- `0 <= intervals.length <= 10^4`
- `intervals[i].length == 2`
- `0 <= intervals[i][0] < intervals[i][1] <= 10^6`

## Follow-ups

- How much work is left if the meetings arrive already sorted by start?
- If they cannot all be attended, how many meetings must be dropped at least (see Non-overlapping Intervals)?
- How many rooms would the meetings need (see Minimum Meeting Rooms)?

## Hints

### Hint 1

If the meetings were listed in order of start time, which pairs could possibly be the first clash?

### Hint 2

Sort by start. The meetings clash exactly when some meeting starts before the one listed just before it ends.

### Hint 3

Ending at `t` and starting at `t` is not a clash, so compare with `<`, not `<=`.
