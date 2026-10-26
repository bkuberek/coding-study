# Fast Power: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| repeated-multiplication | brute | O(n) | O(1) | small exponents only, or as a correctness oracle |
| binary-exponentiation | optimal | O(log n) | O(1) | default answer; also the basis of modular exponentiation |

In the complexity columns, `n` stands for the absolute value of the exponent. Both approaches handle a negative exponent the same way: `x^n = (1 / x)^(-n)`. The difference is how many multiplications they spend: `|n|` versus about `2 log2 |n|`.

## Approach: repeated-multiplication (Multiply |n| times with early stops)

### Intuition

The definition of a power is repeated multiplication, so multiply 1 by the base `|n|` times. Two observations keep the extreme cases from taking billions of steps: once the product is 0 or infinite it can never change again, and if the product returns to exactly 1 after `k` steps, the powers repeat with period `k` (this happens only for `x = 1` and `x = -1`), so only `|n| mod k` more steps matter.

### Algorithm

1. Let `base = x` if `n >= 0`, otherwise `1 / x`; let `remaining = |n|`, computed in 64 bits.
2. Starting from `result = 1`, multiply `result` by `base` one step at a time until `remaining` steps are done:
   1. If `result` becomes exactly 1 after `done` steps, set `remaining = (remaining - done) mod done` and restart the step count.
   2. If `result` becomes 0 or infinite, stop.
3. Return `result`.

### Correctness

Without the early stops, the loop computes `base^|n|`, which is `x^n` for either sign of `n`. Stopping at 0 or infinity is safe because multiplying 0 or infinity by a finite non-zero base gives the same value. When `base^done` is exactly 1, the sequence of products from that point repeats the sequence from the start, so the remaining `remaining - done` steps give the same result as `(remaining - done) mod done` steps.

### Complexity

- Time: O(n) — one multiplication per unit of the exponent; the early stops only shorten degenerate cases (bases 0, 1, -1, and results that underflow or overflow).
- Space: O(1) — a few scalars.

### Trade-offs

Obviously correct and a good oracle, but useless for large exponents with ordinary bases: `1.0000001^2000000000` would take two billion multiplications. Its rounding error also grows linearly with the number of steps, while squaring rounds only O(log n) times.

### Pitfalls and edge cases

- `abs(-2^31)` does not fit in a 32-bit `int`: in Java, `Math.abs(Integer.MIN_VALUE)` is still negative. Widen to `long` before taking the absolute value.
- Compute `1 / x` once, rather than dividing at the end: `1 / x^|n|` overflows to infinity before it can underflow back, which gives 0 here only by luck.

## Approach: binary-exponentiation (Square the base and halve the exponent)

### Intuition

Write the exponent in binary: `n = b0 + 2 b1 + 4 b2 + ...`. Then `x^n` is the product of `x^(2^i)` over the set bits `b_i`, and the powers `x, x^2, x^4, ...` are obtained by squaring the previous one. So read `n` from its lowest bit upwards, square the base at each step, and multiply it into the result whenever the current bit is 1.

### Algorithm

1. Move `n` into a 64-bit `exponent`. If it is negative, replace `x` with `1 / x` and `exponent` with `-exponent`.
2. Set `result = 1`. While `exponent > 0`:
   1. If `exponent` is odd, multiply `result` by `x`.
   2. Square `x` and halve `exponent` (dropping its lowest bit).
3. Return `result`.

### Correctness

Invariant: `result * x^exponent` equals the original `x^n` (after the sign adjustment). It holds initially. If `exponent` is odd, `x^exponent = x * x^(exponent - 1)`, so moving one factor `x` into `result` keeps the product. Then `exponent` is even and `x^exponent = (x^2)^(exponent / 2)`, which squaring and halving preserves. When `exponent` reaches 0 the invariant reads `result * 1 = x^n`.

### Complexity

- Time: O(log n) — the exponent loses one bit per iteration, so there are at most 32 iterations for a 32-bit exponent, each with at most two multiplications.
- Space: O(1) — iterative, no recursion.

### Trade-offs

The expected answer, and the same loop computes modular powers (`result = result * x mod m`) used in hashing and cryptography. A recursive version (`half = pow(x, n / 2)`, then `half * half`, times `x` if `n` is odd) is equally fast and some find it easier to explain; it uses O(log n) stack.

### Pitfalls and edge cases

- Negating `n = -2^31` in 32-bit arithmetic overflows back to `-2^31`, which makes the loop never run (or run forever, depending on the loop condition). Widening to `long` first fixes it in Java and Kotlin.
- Squaring `x` after the last useful bit can overflow to infinity even though the result is fine; it is harmless here because that square is never multiplied in.
- `0^n` for `n > 0` is 0 and comes out naturally; `0` to a negative power is excluded by the constraints.

### Language notes

- Python: integers are unbounded, so `-n` is always safe; `n & 1` and `n >>= 1` read the bits.
- TypeScript: numbers are doubles, so `-n` is exact even for `-2^31`; but the bitwise operators (`&`, `>>`) work on 32-bit signed integers, and `2^31 >> 1` would become negative. The reference uses `% 2` and `Math.floor(exponent / 2)` instead.
- Java: `long exponent = n` widens before negating; `exponent >>= 1` on a non-negative `long` is a plain halving.
- Kotlin: `n.toLong()` widens; bit operations are infix functions (`exponent and 1L`, `exponent shr 1`), and `and` binds more loosely than `==`, so `(exponent and 1L) == 1L` needs the parentheses.
