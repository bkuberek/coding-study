# Car Fleet

## Statement

Several cars drive along the same single-lane road toward a destination at mile `target`. Car `i` starts at mile `position[i]` and drives at a constant `speed[i]` miles per hour. No two cars start at the same mile.

Nobody can overtake on this road. When a car catches up with a slower car ahead of it, it slows down and from then on drives right behind it, at the slower speed; from that moment the two (or more) cars move as one group, a fleet. A single car that nobody catches is a fleet on its own. Cars that catch up exactly at the destination still count as one fleet.

Return the number of fleets that arrive at the destination.

Reference: this is our own wording of LeetCode problem 853, [Car Fleet](https://leetcode.com/problems/car-fleet/).

## Input

- `target`: the mile of the destination
- `position`: the starting mile of each car
- `speed`: the speed of each car, in miles per hour; `speed[i]` belongs to the car at `position[i]`

## Output

The number of fleets that reach mile `target`.

## Examples

### Example 1

<!-- case: ex1 -->

The cars at miles 18, 14 and 10 would all arrive at hour 2 on their own, so the two behind reach the leader exactly at the destination: one fleet. The car at mile 4 needs 16 hours. The car at mile 0 would need only 5, so it catches up with the car at mile 4 on the way and finishes with it: a second fleet.

### Example 2

<!-- case: ex2 -->

All cars drive at the same speed, so no gap ever closes: every car arrives as its own fleet.

## Constraints

- `1 <= position.length <= 10^5`
- `speed.length == position.length`
- `1 <= target <= 10^6`
- `0 <= position[i] < target`, and all positions are distinct
- `1 <= speed[i] <= 1000`

## Follow-ups

- Comparing every car with every car ahead costs O(n^2). Which order of the cars lets you decide each one with a single comparison?
- Can you compare arrival times without division, using integers only?
- With positions bounded by `target`, can you avoid the comparison sort?

## Hints

### Hint 1

Whether a car is caught depends only on when it would arrive alone: `(target - position) / speed`. A car behind with an earlier or equal arrival time joins the fleet ahead of it.

### Hint 2

Process the cars from the one closest to the destination backwards. A car either joins the fleet directly ahead of it or starts a new, slower fleet.

### Hint 3

Going the other way, from the car farthest back toward the destination, keep a stack of fleet arrival times: each new car pops every fleet behind it that arrives no later than it does, because they catch up with it.
