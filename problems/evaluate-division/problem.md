# Evaluate Division

## Statement

Some variables stand for unknown positive numbers. You are told the value of certain quotients: equation `i` says that `equations[i][0] / equations[i][1]` equals `values[i]`. The equations never contradict each other.

Then you get a list of questions. Question `j` asks for the value of `queries[j][0] / queries[j][1]`. Answer it when the equations determine that quotient; otherwise answer `-1.0`. A quotient is determined exactly when the two variables are linked by a chain of equations (each equation may be used in either direction). A variable that appears in no equation is unknown, so any question that mentions it, even `x / x`, gets `-1.0`.

Reference: this is our own wording of LeetCode problem 399, [Evaluate Division](https://leetcode.com/problems/evaluate-division/).

## Input

- `equations`: pairs of variable names `[a, b]`.
- `values`: `values[i]` is the value of `a / b` for `equations[i]`.
- `queries`: pairs of variable names `[c, d]`, each asking for `c / d`.

## Output

An array with one number per question, in question order: the value of the quotient, or `-1.0` when the equations do not determine it. Answers within `10^-5` of the exact value, relative to its size, are accepted.

## Examples

### Example 1

<!-- case: ex1 -->

`x1 / x3` is `(x1 / x2) * (x2 / x3) = 4.0 * 0.25 = 1.0`. `x3 / x2` reverses the second equation: `1 / 0.25 = 4.0`. `x5 / x4` reverses the third: `1 / 2.5 = 0.4`. No chain of equations links `x1` with `x4`, so that question gets `-1.0`. `x2 / x2` is `1.0` because `x2` is known, while `x6` appears in no equation, so even `x6 / x6` is `-1.0`.

### Example 2

<!-- case: ex2 -->

With `a / b = 0.5`, the quotient `b / a` is `2.0`. The variable `c` is unknown, so `a / c` gets `-1.0`.

## Constraints

- `1 <= equations.length <= 1000`, and `values.length == equations.length`
- `1 <= queries.length <= 1000`
- Variable names have 1 to 5 characters, lowercase letters and digits.
- In each equation the two names differ.
- `0.05 <= values[i] <= 20.0`
- The equations are consistent: every chain between two variables gives the same quotient.

## Follow-ups

- How would you detect that a new equation contradicts the earlier ones?
- Many more questions than equations: can you answer each question in near-constant time after some preparation?
- What if the equations arrive one at a time, interleaved with questions?

## Hints

### Hint 1

Draw a graph: one node per variable, and for `a / b = v` an edge from `a` to `b` with weight `v` and an edge from `b` to `a` with weight `1 / v`.

### Hint 2

The answer to `c / d` is the product of the weights along any path from `c` to `d`. A breadth-first or depth-first search finds one, or shows there is none.

### Hint 3

To avoid one search per question, store for every variable its ratio to a representative of its group. Then `c / d = ratio(c) / ratio(d)` whenever both have the same representative.
