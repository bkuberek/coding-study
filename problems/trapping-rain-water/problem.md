# Trapping Rain Water

## Statement

A strip of terrain is made of bars of width 1 standing side by side, with no gaps; bar `i` has height `height[i]`. After a long rain, water collects in every dip of the terrain and stays there wherever it is walled in on both sides. Water above the first or last bar runs off, because nothing holds it on the outside.

Compute the total amount of water held by the terrain, in units of one bar width by one height step.

Reference: this is our own wording of LeetCode problem 42, [Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water/).

## Input

- `height`: the height of each bar, from left to right

## Output

The total number of water units the terrain holds.

## Examples

### Example 1

<!-- case: ex1 -->

The tallest bar on the left is 4 and on the right is 5, so the water in between rises to level 4. Above the bars of height 1, 3, 0 and 2 it holds 3 + 1 + 4 + 2 = 10 units.

### Example 2

<!-- case: ex2 -->

The two bars of height 1 sit between walls of height 3 and 2, so each holds 2 - 1 = 1 unit. The bars of height 0 at the ends hold nothing: one side of each is open.

## Constraints

- `1 <= height.length <= 10^5`
- `0 <= height[i] <= 10^4`

## Follow-ups

- The water above bar `i` depends on the tallest bar to its left and the tallest bar to its right. Can you avoid rescanning for those for every bar?
- Can you compute the total in one pass with O(1) extra memory?
- How would you compute the water if the terrain were a 2D grid of heights instead of a row?

## Hints

### Hint 1

Look at a single bar. How high can the water above it rise, given the bars on either side of it?

### Hint 2

The water level above bar `i` is the smaller of the tallest bar at or left of `i` and the tallest bar at or right of `i`. Both maxima can be precomputed for every position in two passes.

### Hint 3

Walk inward from both ends, keeping the tallest bar seen on each side. Whichever side has the smaller maximum so far already knows its water level: the other side is guaranteed to have a wall at least that tall.
