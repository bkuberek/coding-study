# Water on Terrain

## Statement

Build `Terrain`, a small simulation of rain on a landscape seen from the side. The landscape is a row of columns, and each column has a height: the list `[3, 1, 2, 0, 4]` is five columns side by side, as tall as 3, 1, 2, 0 and 4 squares. You will first draw it as text, then pour water on it one drop at a time and follow exactly where every drop goes, and finally draw the landscape and the water together. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Heights as a picture.** Column 0 is the leftmost one. To see the profile `[3, 1, 2, 0, 4]`, stand the columns up and look at them: the tallest column reaches row 4, so there are four rows, and a cell is filled when its column is at least as tall as that row.

```text
....#     row 4
#...#     row 3
#.#.#     row 2
###.#     row 1
```

This is the text your class returns. What makes the later levels harder is that this is not a picture of a fixed shape: the water you pour changes it, and the rules for where a drop of water goes must be followed to the letter, because there is exactly one right answer for each drop. This is not the question "how much rain does the terrain hold?" that is often asked about such profiles. That question has a formula. Here you simulate drops one at a time, and a flat stretch or an edge changes where the next drop goes.

Aim to finish in 60 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 20, level 2 by 40, level 3 by 48 and level 4 by 55, keeping the last minutes for a final run.

## Input

- `Terrain(heights)`: creates a landscape from a list of non-negative integers, one per column, from left to right. Initially there is no water.
- Columns are numbered from 0. Every column number passed to a method names a column of the landscape.
- Each level's section describes the methods it adds and their parameters.

## Output

Pictures are lists of text rows, from the top row to the bottom row, all of the same length. Water is reported as a list with one whole number for each column: the depth of water in it, in squares.

## Level 1: Drawing the profile

- `render()`: the picture of the landscape, one string per row from the top row down to row 1, as in the drawing above. The number of rows is the height of the tallest column. Row `r` has a `#` in column `c` when the height of column `c` is at least `r`, and a `.` otherwise. A landscape whose columns all have height 0 has no rows: the picture is an empty list.
- `tallest()`: the height of the tallest column, 0 when all are 0.

### Example 1

<!-- case: ex1 -->

The drawing from the statement: the tallest column has height 4, so there are four rows, and the bottom row has a `.` only above column 3, which has height 0.

### Example 2

<!-- case: ex2 -->

Columns of height 0 at both ends and in the middle leave a `.` in every row. The tallest column is the one of height 3.

## Level 2: One unit of water

Water is poured one unit at a time, and a unit is one square of water. Water lies on top of the terrain: the **level** of a column is its height plus the depth of the water in it, and it is the level, not the height, that decides how water moves. A unit that has come to rest raises the level of its column by one.

- `pour(column)`: pours one unit of water on `column` and returns the depth of water in every column afterwards.
- `water()`: the depth of water in every column now, without pouring.
- `spilled()`: the number of units that have fallen off an edge so far.

**Where one unit goes.** The unit lands on `column` and then tries to move, first to the left and, only if the left does nothing, to the right. To try a direction, it walks away from `column` one column at a time:

1. It may step onto the next column only if that column's level is **not higher** than the level of the column it is standing on. A step onto a column of the same level is allowed (a flat stretch), and so is a step down. A higher column stops the walk.
2. If the next step leaves the landscape, because the unit is standing on column 0 and walking left, or on the last column and walking right, the unit **falls off the edge** and is gone. It is counted by `spilled()` and adds no water. This beats everything else: a walk that can reach an edge always ends there.
3. Otherwise the walk ends at the last column it reached. Look at the final flat stretch of the walk, the columns the walk crossed at the same level as that last column, and take the one **nearest to `column`**. If its level is lower than the level of `column`, the unit settles there and its depth of water grows by one, and this direction is done. If it is not lower, because the walk never went down, this direction does nothing.

If the left does nothing, the right is tried the same way. If neither does anything, the unit stays where it landed and the depth of water in `column` grows by one.

Two consequences are worth keeping in mind. A unit poured on column 0 always falls off to the left, since its first step is off the landscape. And the left is always tried first, so when a walk to the left can reach the edge, the unit falls off even if there is a hollow on the right.

### Example 1

<!-- case: ex3 -->

The landscape is `[5, 2, 3, 2, 4]` and every unit is poured on column 2, whose height is 3. The first unit walks left onto column 1 (level 2, lower) and settles there, since column 0 is higher. The second finds the left flat at its own level, which does nothing, so it goes right and settles in column 3. The third finds both sides at its level and stays. The fourth finds the level of column 2 raised to 4: it walks left onto column 1 (level 3) and settles there.

### Example 2

<!-- case: ex4 -->

On `[5, 3, 2, 1]` a unit poured on column 1 cannot go left (column 0 is higher) and slides down the slope to the right, off the edge. A unit poured on the last column is already at the right edge, with a higher column at its left, so it falls off to the right. A unit poured on column 0 falls off to the left.

## Level 3: Many units

- `pourMany(column, units)`: pours `units` units of water on `column`, **one after the other**, each by the rules of level 2 and seeing the water of the units before it, and returns the depth of water in every column afterwards. `units` may be 0.

The units are not poured at once: the second unit walks on the level that the first one left, which is why the water fills a hollow from the bottom up and from the landing column outwards. `pourMany(column, 3)` ends up as three calls to `pour(column)`.

### Example 1

<!-- case: ex5 -->

The hollow in the middle of `[3, 0, 0, 2, 4]` takes six units. After that the water level is 3, the height of the column to its left, and every further unit that lands in the hollow walks left across the flat water and off the edge, although the rim on the right is the lower one: the four units of the second call all spill.

### Example 2

<!-- case: ex6 -->

The landscape is `[2, 0, 1, 0, 3]`. Two units poured on column 2 settle one in each hollow, first on the left and then on the right. The next three are poured on the last column and walk down to the hollow next to it. The last call pours three more on column 2.

## Level 4: Terrain and water together

- `render()` now draws the water too. The picture has one row for each level up to the highest level of any column, terrain and water together. A cell is `#` when the column's height reaches that row, `~` when the row is above the terrain but not above the water, and `.` otherwise. With no water, the picture is the same as before.
- `renderWindow(first, last)`: the picture of the columns from `first` to `last`, both included, with the same rows as `render()` has for the whole landscape: a window always has as many rows as the full picture, even when the tallest column is outside it.

### Example 1

<!-- case: ex7 -->

Three units poured on column 2 of `[3, 0, 0, 2, 4]` leave water in columns 1 and 2. The picture marks it with `~`, below the highest level. After three more units the hollow holds water 3 deep in columns 1 and 2.

### Example 2

<!-- case: ex8 -->

Four units fill the two columns of the first hollow. The window of columns 1 to 3 has the four rows of the full picture, and the window of one column shows column 4 only. The full width gives the picture of the whole landscape.

## Constraints

- At most 5,000 calls per test.
- `1 <= heights.length <= 200` and `0 <= heights[i] <= 40`.
- `0 <= column < heights.length` and `0 <= first <= last < heights.length`.
- `0 <= units <= 20000`.

## Follow-ups

- The well-known question on terrains like this asks how much water they can hold, and has a formula that needs no simulation. Does it give the same answer as running `pourMany` until nothing more stays, and if not, why? What does your simulation do with a hollow next to the left edge?
- `pourMany` costs O(n) per unit, so 20,000 units on 200 columns is 4 million steps. How would you pour `10^9` units on a landscape of 200 columns without going one at a time, once the water in each hollow has reached its final level?
- Make the edges walls instead of cliffs. Which of the rules change, and what happens to a unit that is poured on column 0?
- Add wind: the unit tries the right first on every other drop. What would you have to change in the code, and in the data?

## Hints

### Hint 1

A list of heights is just numbers. To draw it, think of one row at a time. Start with the row at the top, whose number is the largest height, and for each column write a `#` when the column is at least that tall and a `.` when it is not. Then go to the next row down, until row 1.

### Hint 2

You only need to know the tallest height to know how many rows there are. A loop over the rows from that height down to 1, with an inner loop over the columns, builds the picture.

### Hint 3

For water, keep a second list with the depth of water in each column, starting with zeros. The level of a column is `heights[c] + water[c]`. A helper `level(c)` will save you from mixing the two up.

### Hint 4

Write the walk as a helper that takes a start column and a direction (`-1` or `1`) and answers one of three things: "falls off the edge", "settles at column x" or "does nothing". Use `pour` to call it for the left, then for the right, and let `pour` decide what to do with each answer.

### Hint 5

In the walk, move one column at a time while the next column's level is not higher than the current one. Remember the column where the level last went *down*: that is the first column of the final flat stretch, the one nearest to the start. When the walk stops, that column is where the unit settles, if its level is lower than the start's.

### Hint 6

Check for the edge before you look at the next column's level, since there is no next column there. And do not forget that a flat stretch that runs to an edge counts as reaching the edge.

### Hint 7

`pourMany` is a loop that calls the single-unit step. Do not compute the final water in one go, because every unit changes the levels that the next one walks on.

### Hint 8

For the picture, the top row is the highest level (height plus water) over all columns. Then, for each row and column: `#` if the height reaches the row, `~` if the level reaches it, `.` otherwise. For a window, use the same top row as for the full picture and only loop over the columns of the window.
