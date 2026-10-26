# Max Points on a Line: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| check-every-line | brute | O(n^3) | O(1) | a few dozen points, or as a correctness oracle |
| slope-hashing | optimal | O(n^2 log C) | O(n) | default answer |

`n` is the number of points and `C` the coordinate range (the gcd of two differences costs O(log C)). Both approaches use exact integer arithmetic; floating-point slopes are the classic way to get this problem wrong.

## Approach: check-every-line (Count the points on the line through every pair)

### Intuition

Every line that holds two or more input points passes through some pair of them. So try the line through each pair and count the points on it. A point `(x, y)` is on the line through `(x1, y1)` with direction `(dx, dy)` exactly when the cross product `dy * (x - x1) - dx * (y - y1)` is zero, an integer test with no division.

### Algorithm

1. If there are at most two points, return their number.
2. For every pair `i < j`, let `(dx, dy)` be the difference of the two points.
3. Count the points `(x, y)` with `dy * (x - x1) == dx * (y - y1)` (this includes both points of the pair) and keep the maximum.

### Correctness

Take a line holding the maximum number `k >= 2` of points and two of its points; when the loop reaches that pair, it counts exactly the points on that line, because the cross product is zero precisely for points on the line through two distinct points. Every counted value is the size of a real collinear set, so the maximum is exactly `k`. With fewer than three points, every point set is collinear.

### Complexity

- Time: O(n^3) — n(n - 1)/2 pairs, each tested against all n points.
- Space: O(1) — a counter and the best value.

### Trade-offs

No hashing, no gcd, no sign conventions: the cross product handles vertical, horizontal and slanted lines uniformly. That makes it a trustworthy oracle, but the cubic time is too slow at n = 300 in an interpreted language.

### Pitfalls and edge cases

- Products of two differences reach `(2 * 10^4)^2 = 4 * 10^8`, which fits in a 32-bit `int`; with coordinates up to `10^9` you would need 64 bits.
- Comparing `dy / dx` as floating point breaks for vertical lines (`dx = 0` gives infinities of either sign, or a division error with integers), treats `-0.0` and `0.0` as different hash keys in Java and Kotlin, and with larger coordinates lets distinct slopes round to the same double.
- A slope alone does not identify a line: parallel lines share it (case `h10`). That is why the optimal approach groups directions per anchor point.

## Approach: slope-hashing (Group the other points by reduced direction from each anchor)

### Intuition

Fix an anchor point. The lines through it are determined by direction alone, and two other points lie on the same line through the anchor exactly when their directions from it are parallel. If each direction gets one exact canonical key, a hash map counts the points per line through the anchor in one pass. The canonical key of `(dx, dy)` is that vector divided by `gcd(|dx|, |dy|)`, with the sign chosen so that `dx > 0`, or `dx == 0` and `dy > 0`.

### Algorithm

1. Set `best = 1`.
2. For each anchor `i`:
   1. Start an empty map from direction to count.
   2. For each later point `j`, compute `(dx, dy)`, divide both by their gcd, normalize the sign, and increment the count of that direction.
   3. Update `best` with the largest count plus one (the anchor itself).
3. Return `best`.

### Correctness

Two non-zero vectors are parallel exactly when their reduced forms are equal up to sign, and the sign rule picks one of the two, so the map's keys are in one-to-one correspondence with the lines through the anchor that hold a later point. The count of a key is the number of later points on that line. Consider an optimal line and its earliest point in the input order: when that point is the anchor, every other point of the line comes later and falls under the same key, so `best` reaches the optimum; it never exceeds it, since every count is a real collinear set. Considering only later points is enough because an earlier point on the same line was already handled when the earliest point of that line was the anchor.

### Complexity

- Time: O(n^2 log C) — n(n - 1)/2 directions, each with a gcd of O(log C) steps and an average O(1) map update.
- Space: O(n) — the map holds at most n - 1 directions for one anchor.

### Trade-offs

The standard answer. The details carry all the risk: the gcd reduction, the sign convention and an exact key. Alternatives for the key are a pair or tuple (Python), a string such as `"3/-2"` (slower), or one integer that packs both components, as the TypeScript, Java and Kotlin references do.

### Pitfalls and edge cases

- Without a sign rule, `(1, -2)` and `(-1, 2)` describe the same line but get different keys (case `h7`).
- Normalizing only `dx` by its sign misses the vertical case: `(0, 3)` and `(0, -3)` must both become `(0, 1)`.
- The gcd is never 0 because the points are distinct; with duplicate points allowed, duplicates would need a separate counter.
- The answer for a single point is 1, so start `best` at 1 rather than 2.

### Language notes

- Python: `math.gcd` accepts negative arguments and returns a non-negative result; tuples are hashable keys, so `(dx, dy)` works directly with `Counter`.
- TypeScript: there is no tuple key with value equality in `Map`, so the reference packs the direction into one number, `dx * 100000 + dy`, which is unique because `|dy| <= 2 * 10^4`.
- Java: the same packing into a `long` key avoids allocating a key object per pair; `merge` returns the updated count.
- Kotlin: a `tailrec` gcd compiles to a loop; the packed `Long` key is built from an `Int` times a `Long` constant, which widens automatically, and `merge` updates the count with one hash lookup.
