# Debug: Leaderboard Comparator

## Statement

A tournament leaderboard lists players from best to worst. `names[i]` scored `scores[i]` points. The function `rankPlayers` you start from should return the names in leaderboard order:

1. Higher score first.
2. Players with exactly the same score are listed by name in ascending order (plain character-code order; all names are lowercase ASCII).

The code sorts with a hand-written comparator. It passes some tests and fails others. Find the bugs and fix them.

### Bug report

> **Title:** Leaderboard order looks random near close scores; charity event inverted the podium
>
> Players report that someone with 42 points is sometimes listed below someone with 41. It seems to happen when the names are in the "wrong" alphabetical order, and on a long board the order of a group of close scores changes depending on the order in which results were submitted. Scores used to be averages of judges' marks, stored as decimals; since this season they are integer points. Separately, in the charity event, where penalty rounds push scores far below zero and the jackpot round awards up to two billion points, the JVM services put the jackpot winner at the bottom of the board. The Python and TypeScript services did not show that second problem.

## Input

- `names`: distinct player names, lowercase ASCII letters
- `scores`: `scores[i]` is the score of `names[i]`

## Output

The names in leaderboard order: score descending, then name ascending among equal scores.

## Examples

### Example 1

<!-- case: ex1 -->

`ben` and `cy` share the top score of 50, so they appear in name order, followed by `ana` (30) and `dee` (10). This case passes as shipped.

### Example 2

<!-- case: ex2 -->

Everyone is tied on 7, so the whole board is in name order. This case passes as shipped too.

## Constraints

- `1 <= names.length == scores.length <= 1000`
- `-2^31 <= scores[i] <= 2^31 - 1`
- Names are distinct, 1 to 10 lowercase ASCII letters.

## Follow-ups

- What three properties must every comparator satisfy, and which one does a "within epsilon means equal" rule break?
- How would you assign shared ranks (1, 1, 3) to equal scores after sorting?

## Hints

### Hint 1

Reproduce the first complaint with the fewest players you can: two players, one point apart, with names in the opposite order to their scores.

### Hint 2

Read the comparator one branch at a time. When does it ignore the scores entirely? Does that rule still make sense for integer points?

### Hint 3

A comparator defines a total order only if "ties with" is transitive. With the shipped rule, 3 ties with 4 and 4 ties with 5. Does 3 tie with 5?

### Hint 4

For the JVM complaint, compute `2000000000 - (-2000000000)` in 32-bit arithmetic. What sign does the comparator return?
