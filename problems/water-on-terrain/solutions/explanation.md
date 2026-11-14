# Water on Terrain: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| simulate-each-unit | optimal | O(n) per unit poured; O(n h) per picture | O(n) | default answer; the rules are a walk, and the walk is the code |

Here `n` is the number of columns and `h` the highest level of any column.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Draw the profile | `heights`; `render` loops over the rows from the top, then over the columns |
| 2 | One unit of water | `depths` (a depth per column), `spilledUnits`, and two helpers: `walk` (where does a unit go in one direction) and `drop` (try left, then right, else stay) |
| 3 | Many units | nothing new: `pourMany` calls `drop` in a loop |
| 4 | Water in the picture | nothing new: `picture` reads `level` as well as `heights`, and takes a range of columns |

The choice that keeps the later levels small is one helper, `level(c) = heights[c] + depths[c]`, used by the walk and by the picture. The walk never looks at `heights` or `depths` directly, so the rule "water lies on top of the terrain" is written once, and level 4 draws exactly what level 2 moves on.

## Approach: simulate-each-unit (Simulate each unit as a walk to the left and then to the right)

### Intuition

The rules of the statement are already an algorithm: a unit lands, looks left, looks right, and settles. There is no cleverness to find, only exactness. The walk in one direction is monotone: it never goes uphill, so its levels only go down or stay the same. That makes the "lowest column reached, nearest to the start" of the statement simply the first column of the flat stretch where the walk ends, and it can be kept with one variable while walking.

### Algorithm

1. Keep `heights`, a `depths` array of zeros, and a count of spilled units.
2. `walk(column, step)` starts at `column` with `flatStart = column` and moves one column at a time in direction `step`. If the next position is outside the landscape, it answers "spill". If the next column's level is higher than the current one, the walk stops. Otherwise, if the next level is lower than the current one, `flatStart` becomes that column; then the walk moves onto it.
3. When the walk stops, it answers `flatStart` if the level at `flatStart` is lower than the level at `column`, and "does nothing" otherwise.
4. `drop(column)` tries `walk(column, -1)` and, only when that does nothing, `walk(column, +1)`. A "spill" adds one to the spilled count and ends. A column adds one to that column's depth and ends. When both do nothing, the depth of `column` grows by one.
5. `pour` is `drop` followed by a copy of `depths`; `pourMany` is `drop` in a loop of `units`; `water` and `spilled` read the state.
6. `picture(first, last)` finds the highest level over *all* columns, and for each row from there down to 1 writes `#` where the height reaches the row, `~` where only the level does, and `.` elsewhere, for the columns `first` to `last`. `render` is `picture` over every column.

### Correctness

The walk visits a column only when its level is not higher than the previous one, so the levels along it never rise. The final flat stretch therefore holds the lowest level seen, and `flatStart`, which moves only on a strict drop, is the first column of that stretch, that is, the nearest to the landing column among the columns of the lowest level, as the statement says. Comparing its level with the starting level decides between "settles" and "does nothing" in the way the statement does, and the check for the edge comes before the comparison of levels, so a walk that can leave the landscape always does, whatever the levels. Trying left first and right second, and staying only when both do nothing, is the order of the statement. Each unit changes exactly one depth, or the spilled count, so the water moves with the units one at a time, which is what `pourMany` needs.

### Complexity

- Time: O(n) per unit poured; O(n h) per picture — a walk visits each column at most once, and a unit makes at most two walks; a picture writes one cell for each of the `h` rows and up to `n` columns.
- Space: O(n) — the heights and the depths each hold one number per column, and a picture is built row by row.

### Trade-offs

- Each unit costs O(n) however large the landscape is. For many units on a small landscape (the constraints allow 20,000 on 200 columns), that is a few million steps. For billions of units, the water of each hollow could be filled in one step, up to its next spill level, but that is a different algorithm and its tie rules have to match the walk's exactly.
- Keeping `level` in a third array would make the walk faster by one addition per step, and would have to be updated in step with `depths`; with one helper there is a single place to get wrong.
- The formula for the water a terrain can hold (the largest wall on each side, minus the height) answers a different question: it assumes walls at the edges and says nothing about where a given unit goes or how many leave over the edges.

### Pitfalls and edge cases

- Stopping at the first lower column instead of the end of the downhill run: a unit that lands on a slope slides to the bottom of it.
- Taking the farthest column of the final flat stretch instead of the nearest, or the nearest column of *any* flat stretch on the way.
- Treating a flat step as a wall: water crosses a flat stretch, so a step onto an equal level is allowed.
- Treating the edges as walls: the edge is a cliff. A flat stretch that runs to the edge spills, and so does a unit poured on column 0.
- Trying the right before the left, or trying the right when the left spilled.
- Forgetting the water already in a column: a column's level is its height plus its depth, and units poured later walk on the raised levels.
- `pourMany` computing all the destinations on the levels of the start: each unit must see the units before it.
- A window that computes its number of rows from its own columns: a window has the rows of the full picture.
- A picture whose top row is the tallest *height*, not the highest *level*: the two are equal here, but only because the water never rises above the tallest terrain column.

### Language notes

- Python and TypeScript build each picture row from a list of cells joined or concatenated; Java and Kotlin use a `StringBuilder`, Go a `strings.Builder` and Rust a `String`.
- Rust takes `i32` for every `int`, so `walk` keeps the position as `i32` to let it go to `-1`, and converts to `usize` only to index.
- Java's `heights` arrives as a `List<Integer>` and is copied into an `int[]` once; the copy also keeps the class safe from later changes to the caller's list.
