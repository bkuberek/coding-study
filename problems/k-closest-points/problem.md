# K Closest Points to Origin

## Statement

You get a list of points on a plane, each given as integer coordinates `[x, y]`, and an integer `k`. Return the `k` points that are nearest to the origin `(0, 0)`, measured by ordinary straight-line (Euclidean) distance.

The inputs are chosen so that the answer is unambiguous: every returned point is strictly closer to the origin than every point left out. Points inside the answer may be at equal distances, and the same coordinates may appear more than once in the list; each occurrence is a separate point. Return the points in any order.

Reference: this is our own wording of LeetCode problem 973, [K Closest Points to Origin](https://leetcode.com/problems/k-closest-points-to-origin/).

## Input

- `points`: the points, each an array `[x, y]`.
- `k`: how many of the closest points to return.

## Output

An array of `k` points from `points` (each as `[x, y]`): the ones closest to the origin, in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The squared distances are 25, 2, 8 and 25. The two smallest belong to `[1, -1]` and `[-2, 2]`. Comparing squared distances is enough: the square root does not change the order.

### Example 2

<!-- case: ex2 -->

`[2, 2]` is at squared distance 8 and `[-3, 1]` at 10, so only `[2, 2]` is returned.

## Constraints

- `1 <= k <= points.length <= 10^5`
- `-10^4 <= x, y <= 10^4`
- The `k`-th smallest distance is strictly smaller than the `(k + 1)`-th, so the answer is unique.

## Follow-ups

- Sorting all points costs O(n log n). Can you do better when `k` is much smaller than `n`?
- Can you find the answer in O(n) time on average?
- How would you keep the `k` closest points up to date while new points keep arriving?

## Hints

### Hint 1

Compare squared distances `x * x + y * y`: they order points exactly like real distances, and they stay integers.

### Hint 2

Keep the `k` closest points seen so far in a max-heap keyed by distance. A new point that is closer than the heap's farthest point replaces it.

### Hint 3

The answer is a set, not an ordering, so you only need to split the points into "the k closest" and "the rest". A quickselect-style partition does that in linear time on average.
