# All Grid Paths

## Statement

A robot stands on the top-left cell of a square grid with `n` rows and `n` columns. In one move it steps either one cell to the right (`R`) or one cell down (`D`); it never moves left, up or off the grid. It wants to reach the bottom-right cell.

A route is written as the string of its moves, in order. List every route, each exactly once. The list must be in lexicographic (dictionary) order with `D` before `R`, so the first string is the one that goes all the way down before turning right and the last one goes all the way right first. The order is part of the answer: there is only one correct list for every `n`.

This is not the problem of counting the routes. Counting needs only a number, and a table or a binomial coefficient gives it in a moment. Here the routes themselves are the answer, so the work is at least as large as the output: there are `C(2n - 2, n - 1)` of them, each `2n - 2` characters long, which is 48,620 strings at `n = 10`. That is why `n` stays small.

## Input

- `n`: the number of rows and the number of columns of the grid

## Output

A list of strings. Each string has `n - 1` letters `D` and `n - 1` letters `R`, and every such string appears exactly once. The strings are in ascending lexicographic order, with `D` before `R`.

## Examples

### Example 1

<!-- case: ex1 -->

A 2 by 2 grid needs one move down and one move right. Going down first gives `DR`, which sorts before `RD`.

### Example 2

<!-- case: ex2 -->

Every route makes 2 moves down and 2 moves right in some order, which gives `C(4, 2) = 6` routes. Reading them in dictionary order with `D` first lists `DDRR` before `DRDR`, and `RRDD` last.

## Constraints

- `1 <= n <= 10`

## Follow-ups

- On a 1 by 1 grid the robot is already at the goal. What is the list of routes?
- Some cells are blocked, given as a grid of 0s (open) and 1s (blocked), and a route may not step on a blocked cell. A blocked start or a blocked goal gives no routes at all. What changes in your search, and does the order of the output stay the same?
- How many strings does your search build that never become routes? Can you make that number zero?

## Hints

### Hint 1

Every route has exactly `n - 1` downs and `n - 1` rights, so the grid size only fixes how many moves of each kind are left to place.

### Hint 2

Build one route move by move. At each step you may add a `D` while fewer than `n - 1` downs are used, and an `R` while fewer than `n - 1` rights are used. When both counts reach `n - 1`, the route is complete: record it.

### Hint 3

Try `D` before `R` at every step, and the routes appear in the order the statement asks for, with no sorting at the end. Remember to undo a move after you come back from exploring it, and to store a copy of the path you are building, not the path itself.
