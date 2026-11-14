# Gas Station

## Statement

`n` fuel stations stand on a circular road, numbered `0` to `n - 1` in driving order. Station `i` lets you fill up `gas[i]` units of fuel, and driving from station `i` to the next one (station `i + 1`, or station `0` after the last) burns `cost[i]` units. Your car has an unlimited tank, which is empty when you start.

Choose a starting station, fill up there, and drive around the circle in order, filling up at every station you reach. You complete the circuit if you arrive back at the starting station without the fuel ever dropping below zero on the way. Return the index of a starting station from which the circuit can be completed, or `-1` if there is none.

The inputs guarantee that when a valid starting station exists, it is the only one.

Reference: this is our own wording of LeetCode problem 134, [Gas Station](https://leetcode.com/problems/gas-station/).

## Input

- `gas`: the fuel available at each station
- `cost`: the fuel needed to drive from each station to the next

## Output

The unique starting index that completes the circuit, or `-1` if no start works.

## Examples

### Example 1

<!-- case: ex1 -->

Start at station 2 and fill up 5 units. Drive to station 3 (4 left), fill up to 5, drive to station 0 (3 left), fill up to 5, drive to station 1 (2 left), fill up to 4, and drive back to station 2 (0 left). The tank never goes negative. Starting at any other station runs dry on the very first leg.

### Example 2

<!-- case: ex2 -->

The stations offer 6 units of fuel in total but the road needs 7, so no starting point can complete the circuit.

## Constraints

- `1 <= gas.length == cost.length <= 10^5`
- `0 <= gas[i], cost[i] <= 10^4`
- If some start completes the circuit, exactly one does.

## Follow-ups

- Simulating the trip from every station takes O(n^2) time. If a trip from station `a` runs dry before station `b`, what does that say about starting anywhere between `a` and `b`?
- Why is a non-negative total of `gas[i] - cost[i]` enough to guarantee that some start works?
- Can you find the start from the running balance alone, without restarting?

## Hints

### Hint 1

If the total fuel is less than the total cost, no start can work. Otherwise, some start does.

### Hint 2

Drive from station 0, tracking the fuel. When it drops below zero after leaving station `i`, no station from your current start up to `i` can be the answer, so restart from `i + 1` with an empty tank.
