# Rotting Oranges

## Statement

A crate of oranges is laid out as a grid. Each cell is empty (`0`), holds a fresh orange (`1`) or holds a rotten orange (`2`). Rot spreads in whole minutes: at the end of every minute, each fresh orange that shares a side (up, down, left or right) with an orange that was already rotten at the start of that minute becomes rotten too. Empty cells block nothing and spread nothing; they simply hold no orange.

Return the number of minutes after which no fresh orange is left. If some fresh orange can never be reached by the rot, return `-1`.

Reference: this is our own wording of LeetCode problem 994, [Rotting Oranges](https://leetcode.com/problems/rotting-oranges/).

## Input

- `grid`: the crate, with `m` rows and `n` columns; `grid[r][c]` is `0` (empty), `1` (fresh) or `2` (rotten).

## Output

The smallest number of minutes after which every orange is rotten; `0` if no fresh orange exists at the start; `-1` if a fresh orange stays fresh forever.

## Examples

### Example 1

<!-- case: ex1 -->

The rot starts in two corners. After one minute it has reached the orange next to the top-left corner and the two oranges next to the bottom-right corner; after two minutes it reaches three more, and in the third minute the last fresh orange, in the bottom-left corner, turns.

### Example 2

<!-- case: ex2 -->

The fresh orange in the bottom-right corner has only empty cells and the grid edge around it, so the rot never reaches it, and the answer is -1, even though the other fresh orange rots after one minute.

## Constraints

- `1 <= m, n <= 100`
- `grid[r][c]` is `0`, `1` or `2`.

## Follow-ups

- Report, for every orange, the minute at which it turns rotten.
- What if rot also spreads diagonally? What if an orange needs two rotten neighbors before it turns?
- Rescanning the grid every minute costs a full pass per minute. How can each orange be handled only once?

## Hints

### Hint 1

The minute at which an orange rots is its distance, in side steps through oranges, from the nearest orange that was rotten at the start.

### Hint 2

Distances from the nearest of several sources are what a breadth-first search computes when all sources start in the queue together.

### Hint 3

Count the fresh oranges first. Every time one rots, decrement the count; if it is not zero when the search ends, some orange was unreachable.
