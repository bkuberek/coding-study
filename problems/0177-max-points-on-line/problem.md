# Max Points on a Line

## Statement

You get `n` distinct points in the plane, each with integer coordinates `[x, y]`. Find the largest number of them that lie on one straight line.

Any line counts: horizontal, vertical or slanted. A single point always lies on a line, and any two points define one, so the answer is at least `min(n, 2)`.

Reference: this is our own wording of LeetCode problem 149, [Max Points on a Line](https://leetcode.com/problems/max-points-on-a-line/).

## Input

- `points`: the points, each `[x, y]`, all distinct

## Output

The largest number of input points on a single line.

## Examples

### Example 1

<!-- case: ex1 -->

The points `[0, 1]`, `[2, 2]`, `[4, 3]` and `[-2, 0]` lie on the line `y = x / 2 + 1`. No other line holds more than two of the six points.

### Example 2

<!-- case: ex2 -->

Three points are stacked on the vertical line `x = 3`. A vertical line has no finite slope, so it needs care when slopes are compared.

## Constraints

- `1 <= points.length <= 300`
- `points[i].length == 2`
- `-10^4 <= x, y <= 10^4`
- All points are distinct.

## Follow-ups

- Checking every line through two points against every point is O(n^3). Can you do O(n^2)?
- Why is a floating-point slope `dy / dx` a risky hash key?
- How would you handle duplicate points if they were allowed?

## Hints

### Hint 1

Fix one point as an anchor. Every line through it is determined by the direction to one other point.

### Hint 2

Two other points are on the same line through the anchor exactly when their directions from it are parallel. Count the points per direction in a hash map.

### Hint 3

Represent a direction exactly as a reduced pair: divide `(dx, dy)` by `gcd(|dx|, |dy|)` and fix the sign (for example, make `dx` positive, or `dy` positive when `dx` is 0). Then parallel directions get identical keys, vertical lines included.
