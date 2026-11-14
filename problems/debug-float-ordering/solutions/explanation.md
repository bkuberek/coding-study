# Debug: Float Ordering: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| defined-rate | optimal | O(n log n) | O(n) | default answer: rate 0 for unseen creatives, `total_cmp` for the order |

## Approach: defined-rate (Define the empty rate and compare with a total order)

### Intuition

A creative that was never shown has `clicks = 0` and `impressions = 0`, so the code computes `0.0 / 0.0`, which is NaN in IEEE 754 floating point. NaN is not equal to, less than or greater than anything, itself included. That is why Rust's `f64` implements `PartialOrd` but not `Ord`: `a.partial_cmp(&b)` returns `None` when either side is NaN. The comparator calls `.unwrap()` on that `None`, and the sort panics the first time it compares the new creative with anything else.

The `partial_cmp(..).unwrap()` idiom is common because `sort()` on floats does not compile, and the unwrap looks harmless as long as nobody thinks about NaN. Every campaign whose creatives were all shown at least once has no NaN and ranks correctly. A campaign with a single creative never compares anything, which is why that one did not panic either.

Two things need fixing. The rate must follow the statement, `0` for a creative that was never shown, so no NaN is created. And the comparator should use a total order, `f64::total_cmp`, so that it always returns an `Ordering` and cannot panic.

### Debugging approach

1. **Read the panic.** ``called `Option::unwrap()` on a `None` value`` points at the only `unwrap` in the function, on the result of `partial_cmp`.
2. **Ask when `partial_cmp` returns `None`.** Only when one of the two values is NaN. So some rate is NaN.
3. **Find where NaN comes from.** The failing campaigns all contain a creative with 0 impressions. `0.0 / 0.0` is NaN (a nonzero number divided by `0.0` would be infinite instead, but `clicks <= impressions` rules that out).
4. **Explain the passing outliers.** A single new creative passes because sorting one element compares nothing. This confirms that the panic happens in the comparator, not in the division.
5. **Fix the data, then the comparator.** `total_cmp` alone stops the panic but still ranks a NaN somewhere, and where depends on the NaN's sign bit (see the pitfalls). The statement defines the rate as 0, so compute 0.

### Algorithm

1. For each creative, compute its rate: `0.0` if it has no impressions, otherwise `clicks / impressions` in `f64`.
2. Sort the pairs `(id, rate)` by rate descending with `b.total_cmp(&a)`, then by id ascending.
3. Return the ids in sorted order.

### Correctness

With the zero-impression case handled, every rate is a finite number in `[0, 1]`, so NaN never occurs. On finite values other than zeros of different signs, `total_cmp` agrees with the usual numeric order; every rate here is `+0.0` or positive (`0.0 / n` is `+0.0`), so the order is the numeric one. Two rates that are equal as fractions are equal as doubles, because IEEE division rounds the exact quotient correctly, so `1/3` and `3/9` tie and fall through to the id comparison, as `h7` checks. The comparator is a total order (rate, then a distinct id), so the sorted order is unique and matches the statement.

### Complexity

- Time: O(n log n) — computing rates is linear, sorting is O(n log n).
- Space: O(n) — the pairs being sorted.

### Trade-offs

`total_cmp` plus an explicit empty rate is short and cannot panic. Alternatives:

- Keep `partial_cmp` but with `.unwrap_or(Ordering::Equal)`: no panic, but NaN then compares equal to everything, which is not a consistent order. Since Rust 1.81 a sort may panic on an inconsistent comparator, and before that it returned an unspecified order.
- Compare fractions exactly with integers: `(b.clicks as i64 * a.shown as i64).cmp(&(a.clicks as i64 * b.shown as i64))`. No rounding at all, but `0/0` against `3/10` gives `0 == 0` and compares as a tie, so the empty case still needs its own rule.
- Wrap the rate in a newtype that implements `Ord` (crates such as `ordered-float` do this), which pays off when floats are sorted or used as map keys in many places.

### Pitfalls and edge cases

- The general trap: `f64` is only partially ordered. `partial_cmp(..).unwrap()`, `max_by(|a, b| a.partial_cmp(b).unwrap())` and similar all panic as soon as a NaN appears, and NaN appears silently from `0.0 / 0.0`, `inf - inf` or `0.0 * inf`.
- `total_cmp` alone is not a fix. It orders a positive NaN above every number and a negative NaN below, and Rust does not specify the sign of a NaN produced by arithmetic. On ARM (Apple silicon) `0.0 / 0.0` is a positive NaN, so a never-shown creative would rank first; on x86-64 the hardware produces a negative NaN, and it would rank last.
- `total_cmp` orders `-0.0` below `+0.0`. Here every rate is non-negative and `0.0 / n` is `+0.0`, so it does not matter; with signed values, normalize zeros or compare differently.
- A creative shown without clicks and one never shown both have rate 0 and tie on id (`h4`).

### Prevention

- Treat every division as a place where NaN or infinity can appear, and decide what the result means when the denominator is 0. Put that decision in a small named function.
- Prefer `total_cmp` over `partial_cmp(..).unwrap()` for sorting floats; clippy has no default lint for the unwrap, so a review rule or a project-wide helper is the guard.
- `debug_assert!(rate.is_finite())` where a value must be a real number turns a later panic far away into one at the source.

### Language notes

- Rust only. Java's `Double.compare` treats NaN as larger than everything, so the same code would silently rank new creatives first; it would not panic. Kotlin's `compareBy`/`sortedByDescending` on `Double` uses the same rule. Python's `sorted` does not raise either, but a NaN key makes the order of the whole list unpredictable, since every comparison with NaN is `False`. Go's `sort.Slice` with `<` behaves like Python; `cmp.Compare` treats NaN as smaller than every number, so `slices.SortFunc` with it never panics either. TypeScript's `(a, b) => b - a` returns NaN, which sorts unpredictably.
- `f64::total_cmp` is the IEEE 754 `totalOrder` predicate; it is stable since Rust 1.62.
