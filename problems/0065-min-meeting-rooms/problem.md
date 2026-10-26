# Minimum Meeting Rooms

## Statement

You are given the schedule of a day's meetings. Meeting `i` occupies a room from time `intervals[i][0]` up to, but not including, time `intervals[i][1]`. A room holds one meeting at a time, and a room freed at time `t` can host a meeting that starts at time `t`.

Return the smallest number of rooms that can host every meeting without moving any of them.

Reference: this is our own wording of LeetCode problem 253, [Meeting Rooms II](https://leetcode.com/problems/meeting-rooms-ii/).

## Input

- `intervals`: the meetings as `[start, end]` pairs, in any order

## Output

The minimum number of rooms, which equals the largest number of meetings in progress at the same moment.

## Examples

### Example 1

<!-- case: ex1 -->

At time 10, the meetings starting at 9 and 10 are both in progress. The meeting `[10, 11]` ends at 11 just as `[11, 13]` starts, and `[9, 12]` ends at 12 just as `[12, 14]` starts, so a third room is never needed.

### Example 2

<!-- case: ex2 -->

Each meeting starts exactly when the previous one ends, so a single room hosts all three.

## Constraints

- `1 <= intervals.length <= 10^5`
- `intervals[i].length == 2`
- `0 <= intervals[i][0] < intervals[i][1] <= 10^9`

## Follow-ups

- Can you return an actual assignment of meetings to rooms?
- What if you only had to decide whether one room suffices?
- How would you report the busiest time of the day as well?

## Hints

### Hint 1

The number of rooms needed is the largest number of meetings that are running at the same moment. At which moments can that largest number first be reached?

### Hint 2

Process meetings in order of start time. When a meeting starts, is there a room that has already been freed? Only the earliest-ending running meeting matters for that question.

### Hint 3

Keep the end times of the running meetings in a min-heap. Before placing a meeting, release a room if the smallest end time is at most its start. Alternatively, sort the start times and the end times separately and sweep both lists with two pointers.
