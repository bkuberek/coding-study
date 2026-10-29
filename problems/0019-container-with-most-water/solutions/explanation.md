# Container With Most Water: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| two-pointers | optimal | O(n) | O(1) | default answer |

## Approach: brute-force (Measure every pair of bars)

### Intuition

The answer is a maximum over all pairs of positions, and the amount for one pair is a single formula. Computing it for every pair and keeping the largest is correct by definition.

### Algorithm

1. Set `best = 0`.
2. For every `left` from 0 to n - 2 and every `right` from `left + 1` to n - 1, set `best = max(best, (right - left) * min(height[left], height[right]))`.
3. Return `best`.

### Correctness

Every pair `i < j` is visited exactly once, and the value computed for it is the statement's formula. The maximum of all those values is returned. There are at least two bars, so at least one pair exists.

### Complexity

- Time: O(n^2) — n(n - 1)/2 pairs, each O(1).
- Space: O(1) — two indices and the running maximum.

### Trade-offs

No insight needed and no way to get it wrong, so it is the oracle. It does about 5 * 10^7 pair checks at n = 10^4, which takes a couple of seconds in Python and would take minutes at the stated maximum of 10^5. It never exploits the fact that, for a fixed short wall, moving the other wall inward can only lose water.

### Pitfalls and edge cases

- The width is `right - left`, not `right - left + 1`: adjacent bars are one unit apart.
- The level is the shorter wall, not the average or the taller one.
- A zero-height wall holds nothing; the answer can be 0, as for `[0, 7]`.
- The largest product, 10^4 * (10^5 - 1), is under 2^31, so 32-bit integers are safe.

### Language notes

- Python: computing `min` with a conditional expression instead of the builtin `min` call roughly halves the cost of the inner loop in CPython; the growth is unchanged.
- TypeScript: `Math.max` and `Math.min` on small integers are inlined by V8.
- Java: `Math.max` and `Math.min` on `int` are intrinsics; no boxing occurs with `int[]`.
- Kotlin: `maxOf` and `minOf` compile to the same JVM calls.
- Go: `min` and `max` are builtins since Go 1.21, so no helper is needed, and `int` is 64-bit, so the area cannot overflow.
- Rust: `i32::min` and `i32::max` are methods on the value. The widths are `usize` differences, converted with `as i32` before the multiplication; the area stays at or below `10^5 * 10^4`, inside `i32`, and cstudy builds Rust with overflow checks, so a wrong type would panic instead of wrapping.

## Approach: two-pointers (Move the shorter bar inward)

### Intuition

Start with the widest container, the two outer bars. Whichever wall is shorter limits the water. Any container that keeps that shorter wall and replaces the other wall with one further inward is narrower and still capped by the same short wall, so it cannot hold more. The shorter wall has therefore already met its best partner, and it can be discarded. Repeating this discards one bar per step, so n - 1 steps examine every pair that could matter.

### Algorithm

1. Set `left = 0`, `right = n - 1`, `best = 0`.
2. While `left < right`:
   1. Compute the water for the current pair and update `best`.
   2. If `height[left] < height[right]`, increase `left`; otherwise decrease `right`.
3. Return `best`.

### Correctness

Claim: when the loop discards a wall, no remaining pair that contains it can beat the value just computed. Say `height[left] <= height[right]` and the loop discards `left`. Any pair `(left, k)` with `left < k < right` has width `k - left < right - left` and level `min(height[left], height[k]) <= height[left]`, so it holds at most `(right - left) * height[left]`, which is exactly the value of the current pair. The case of discarding `right` is symmetric. By induction, every pair that is never evaluated is dominated by one that was, so `best` ends as the maximum over all pairs. On equal heights either wall may go: the argument holds for both.

### Complexity

- Time: O(n) — every iteration moves one pointer inward, so there are exactly n - 1 iterations.
- Space: O(1) — two indices and the running maximum.

### Trade-offs

Linear time, constant memory, a few lines of code. The hard part is the argument, not the code: interviewers usually ask why moving the shorter wall is safe, so be ready to give the domination argument above. A small speed-up skips every bar not taller than the wall just discarded, since such a bar can only produce a smaller container; it keeps the same O(n) bound.

### Pitfalls and edge cases

- Move the shorter wall. Moving the taller one discards pairs that may be optimal: on `[5, 9, 9, 1]` it finds only 3, while the answer is 10.
- Evaluate the current pair before moving a pointer, or the outermost pair (often the answer, as in `[5, 5, 5, 5]`) is never measured.
- The loop condition is `left < right`; a container needs two distinct walls.

### Language notes

- Python: `max(best, ...)` is a builtin call per step; at n = 10^5 that is still only milliseconds.
- TypeScript: plain indices over a `number[]` keep the loop monomorphic and fast.
- Java: the reference uses `int` throughout; the product cannot overflow under the constraints.
- Kotlin: `IntArray` indexing does not box; `maxOf` is the idiomatic `Math.max`.
- Go: a plain `for left < right` loop with the builtin `max`; both indexes are `int`, so the width needs no conversion.
- Rust: the right pointer is stored one past the bar it stands for (`height[right - 1]`), the same trick that keeps an empty input from underflowing `usize`, and the width is converted to `i32` once per step.
