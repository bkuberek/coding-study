# Maximum Average of a Fixed Window: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| recompute | brute | O(n * k) | O(1) | n and k are tiny, or as the obviously correct baseline |
| sliding-window | optimal | O(n) | O(1) | default answer |

A window is a run of `k` neighbouring numbers. There are `n - k + 1` of them, one per start position, and consecutive windows share `k - 1` numbers. The brute force ignores that overlap; the sliding window is the idea of using it.

## Approach: recompute (Add up every window from scratch)

### Intuition

Do exactly what the statement says. For each start position, add up the `k` numbers of the window that begins there, divide by `k`, and keep the largest average.

### Algorithm

1. Set `best` to minus infinity.
2. For every start from `0` to `n - k`: add up `nums[start]` to `nums[start + k - 1]`, divide the sum by `k`, and replace `best` if the average is larger.
3. Return `best`.

### Correctness

Every window of width `k` begins at exactly one start from `0` to `n - k`, and the loop visits each of them, computing the window's true average. The result is the maximum of all those averages, which is the largest average by definition.

### Complexity

- Time: O(n * k) — there are `n - k + 1` windows and each costs `k` additions. The cost peaks when `k` is about `n / 2`, where it is roughly `n^2 / 4`.
- Space: O(1) — a sum and a best value.

### Trade-offs

Clear and almost impossible to get wrong, which is why it serves as the reference to check other answers against. It repeats work: window 2 re-adds `k - 1` numbers that window 1 already added. For `n` = 100,000 and `k` = 50,000 that is over a billion additions.

### Pitfalls and edge cases

- Start `best` at minus infinity (or at the first window's value), not at 0: when every number is negative, a best that starts at 0 is never beaten and the function would return 0.
- The last start is `n - k`, not `n - 1`: a shorter run at the end of the array is not a window.
- Divide as floating point. In Java, Kotlin, Go and Rust the sum is an integer, and dividing two integers would drop the fraction.

### Language notes

- Python: `sum(nums[start : start + k])` copies the slice and adds it in C; the generator expression inside `max` produces one average per start.
- TypeScript: plain `number` arithmetic; `-Infinity` is the starting best.
- Java: `(double) sum / k` casts before dividing; `Double.NEGATIVE_INFINITY` is the starting best.
- Kotlin: `sum.toDouble() / k`, and `0..nums.size - k` is an inclusive range of starts.
- Go: `nums[start : start+k]` is a view of the same array, not a copy; the average is `float64(sum) / float64(k)`, and `math.Inf(-1)` is the starting best.
- Rust: `nums.windows(k)` is a slice method that yields every contiguous run of `k` elements as a slice; per the standard library documentation it panics when `k` is 0, which the constraints rule out. `fold(f64::NEG_INFINITY, f64::max)` keeps the largest average, starting from minus infinity as the other languages do.

## Approach: sliding-window (Slide the window and update its sum)

### Intuition

Two neighbouring windows differ by one number in and one number out. So instead of adding up `k` numbers again, take the previous sum, add the number that enters on the right and subtract the number that leaves on the left. That makes each step constant work. Because every window has the same width `k`, the window with the largest sum also has the largest average, so the loop compares sums, which stay exact integers, and divides by `k` once at the end.

### Algorithm

1. Add up the first `k` numbers into `window_sum`, and set `best = window_sum`.
2. For `right` from `k` to `n - 1`: set `window_sum = window_sum + nums[right] - nums[right - k]`, and set `best = max(best, window_sum)`.
3. Return `best / k` as a floating-point division.

### Correctness

Before step 2 handles position `right`, `window_sum` is the sum of `nums[right - k .. right - 1]`. Adding `nums[right]` and subtracting `nums[right - k]` leaves the sum of `nums[right - k + 1 .. right]`, the next window, so the invariant holds on every pass. Hence `window_sum` takes the value of every window's sum exactly once, `best` ends up as the largest of them, and since all windows share the same width, dividing the largest sum by `k` gives the largest average.

### Complexity

- Time: O(n) — `k` additions for the first window and one addition and one subtraction for each of the other `n - k` windows.
- Space: O(1) — a running sum and a best value.

### Trade-offs

Same answer as `recompute` in a single pass with no extra memory, and the pattern is the starting point for variable-size windows. There, the left edge also moves according to a condition instead of staying exactly `k` behind the right edge. Comparing integer sums instead of floating-point averages also avoids accumulating rounding error from repeated updates of a floating-point running average.

### Pitfalls and edge cases

- Start `best` from the first window's sum, not from 0.
- Do not forget the first window: the loop starts at `right = k`, so the first window must be summed before it.
- `k == n` means there is a single window, and the loop body never runs.
- The sums stay within 32-bit integers: a window sum is at most 10^5 · 10^4 = 10^9, below 2^31 − 1 = 2,147,483,647. In a language with smaller integers or with larger limits, check the arithmetic before relying on this.
- Take the division as the last step, and make it a floating-point division.

### Language notes

- Python: integers never overflow, and `best / k` is a true division that returns a `float`.
- TypeScript: every `number` is a double, so `best / k` needs no cast; the sums are exact because they stay far below 2^53.
- Java: `(double) best / k` converts first, so the division is floating point; `int` is wide enough for the sums, as the comment in the reference explains.
- Kotlin: `best.toDouble() / k`; `for (right in k until nums.size)` is the half-open range of positions.
- Go: `float64(best) / float64(k)`; the built-in `max` function (added in Go 1.21) compares two ints.
- Rust: `nums[..width].iter().sum()` needs the type annotation `i32` on the variable; `f64::from(best) / f64::from(k)` converts both sides exactly, since every `i32` is representable as an `f64`.
