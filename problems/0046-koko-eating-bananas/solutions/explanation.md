# Koko Eating Bananas: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| try-every-speed | brute | O(n * k) | O(1) | the answer is known to be tiny, or as a correctness oracle |
| search-the-speed | optimal | O(n log m) | O(1) | default answer |

`n` is the number of piles, `k` the answer and `m` the largest pile.

## Approach: try-every-speed (Try speeds 1, 2, 3 and so on)

### Intuition

The answer is a positive integer, and checking one candidate speed is easy: add up the hours every pile takes at that speed. Trying 1, 2, 3, ... in order, the first speed that fits is by definition the smallest one.

### Algorithm

1. Start with `speed = 1`.
2. Compute `hours = sum(ceil(p / speed))` over all piles.
3. If `hours <= h`, return `speed`; otherwise increase `speed` by one and repeat from step 2.

### Correctness

Every speed below the returned one was tried and needed more than `h` hours, and the returned one needs at most `h`, so it is the minimum. The loop terminates: at `speed = max(piles)` every pile takes one hour, `n` hours in total, and `n <= h` by the constraints.

### Complexity

- Time: O(n * k) — each candidate costs one pass over the n piles, and the loop tries k speeds, where k is the answer (at most `max(piles)`). The test generator ties the answer to the input size (between n/20 and n/10), so the measured growth is quadratic.
- Space: O(1) — a running total.

### Trade-offs

It is obviously correct and makes a good oracle, but its cost depends on the answer, not just the input size: one pile of 10^9 bananas with `h = 1` would take 10^9 attempts. The hidden tests keep answers small so that it still finishes; on real inputs only a search over speeds is acceptable.

### Pitfalls and edge cases

- `ceil(p / speed)` must be integer arithmetic: `(p + speed - 1) / speed`. Floating-point division is exact here only because the values stay below 2^53.
- The total hours at speed 1 equal the total number of bananas, up to 10^13: a 32-bit counter overflows in Java and Kotlin and the comparison with `h` silently goes wrong.

### Language notes

- Python: integers are unbounded, so `sum(...)` of a generator expression cannot overflow.
- TypeScript: `Math.ceil(pile / speed)` is exact because `pile` and `speed` are integers below 2^31; sums stay below 2^53.
- Java: `(pile + (long) speed - 1) / speed` promotes to `long` before the addition, so neither the numerator nor the total overflows.
- Kotlin: `generateSequence(1) { it + 1 }.first { ... }` expresses "the first speed that fits" lazily; `sumOf` with a `Long` lambda (`speed - 1L`) accumulates in 64 bits.

## Approach: search-the-speed (Binary search on the answer)

### Intuition

Going faster never costs more hours: each `ceil(p / k)` can only shrink as `k` grows. So along the speeds 1, 2, ..., max(piles), the test "finishes within `h` hours" is false for a prefix and true for everything after it. The smallest true speed is a boundary in a monotone sequence, which binary search finds in about log2(max(piles)) tests instead of one test per speed.

### Algorithm

1. Set `low = 1` and `high = max(piles)`; speed `high` always fits, because every pile then takes one hour and `n <= h`.
2. While `low < high`:
   1. Let `speed = (low + high) / 2`, rounded down.
   2. If the piles take at most `h` hours at `speed`, set `high = speed` (it fits, but a slower one might too).
   3. Otherwise set `low = speed + 1` (it is too slow, and so is every slower speed).
3. Return `low`.

### Correctness

Invariant: every speed below `low` is too slow, and `high` fits. Both parts hold initially. If `speed` fits, `high = speed` keeps "high fits". If it does not fit, monotonicity makes every speed up to `speed` too slow, so `low = speed + 1` keeps the first part. Since `low <= speed < high`, each iteration shrinks the range, and the loop ends with `low == high`: a speed that fits, with every slower speed too slow. That is the minimum.

### Complexity

- Time: O(n log m) — about log2(m) iterations, each one pass over the n piles to count hours. In the generated tests m is about 50 times the answer, which itself grows with n, so the measured growth is n log n.
- Space: O(1) — the bounds and a running total.

### Trade-offs

This is the expected answer, and its shape (binary search over the answer with a monotone feasibility check) recurs in `split-array-largest-sum`, shipping capacities, and minimum-time scheduling problems. The bounds can be tightened (the answer is at least `ceil(total / h)` and at most `ceil(max / floor(h / n))`), which saves a few iterations but adds code and risk; mention it rather than implement it.

### Pitfalls and edge cases

- The upper bound is `max(piles)`, not `h` or the total: a speed above the largest pile never helps.
- Use `high = speed` when the speed fits, not `speed - 1`; the current speed may be the answer.
- Count hours in 64 bits in Java and Kotlin, as in the brute force.
- `h == n` forces the answer to be `max(piles)`; a huge `h` forces it to be 1. Both fall out of the loop without special cases.

### Language notes

- Python: `-(-pile // speed)` is ceiling division with floor division; `math.ceil(pile / speed)` goes through a float and could round wrongly for values above 2^53, though not within these constraints.
- TypeScript: `Math.max(...piles)` spreads up to 10^4 arguments, which is fine; for much larger arrays use a loop. `Math.floor((low + high) / 2)` is safe because the sum stays below 2^53.
- Java: `Arrays.stream(piles).max().getAsInt()` gives the largest pile; `low + (high - low) / 2` avoids overflowing `int` when both bounds are near 10^9.
- Kotlin: `piles.max()` is non-null for a non-empty `IntArray` (Kotlin 1.7+); the midpoint uses the same overflow-safe form as Java.
