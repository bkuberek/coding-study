# Debug: Unsigned Underflow: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| half-open-interval | optimal | O(log n) | O(1) | default answer: search `[lo, hi)` so that no bound goes below zero |

## Approach: half-open-interval (Half-open binary search)

### Intuition

Rust indexes slices with `usize`, an unsigned type, so `lo`, `hi` and `mid` are inferred as `usize`. The Java original used `int` and relied on `hi` becoming `-1`:

- With no releases, `hi = len - 1` is `-1` in Java and the loop never runs. In Rust, `0 - 1` on a `usize` is an overflow.
- When `at` is before the first release, the search keeps moving left until `mid` is `0`, then sets `hi = mid - 1`. Java gets `-1`, the condition `lo <= hi` fails, and the method returns `-1`. Rust computes `0 - 1` again.

What happens next depends on the build. With overflow checks on (debug builds, and this problem's test runner), the subtraction panics: `attempt to subtract with overflow`. With them off (the default release profile), it wraps silently to `usize::MAX`, `lo <= hi` is still true, `mid` becomes about 2^63, and indexing panics with `index out of bounds`. Either way the closed-interval search cannot express "empty range" when the range ends below index 0.

The fix is to describe the search space so that no bound ever needs a value below zero: the half-open range `[lo, hi)` starts as `[0, len)`, and is empty when `lo == hi`.

### Debugging approach

1. **Read the panic location.** The runner reports `attempt to subtract with overflow` at `hi = mid - 1` (or at `len() - 1` for an empty list). Only two subtractions exist; both are on `usize`.
2. **Find the input class.** Every failing case has `at` before the first release, or no releases. Every query at or after the first release passes, because then `mid` never reaches 0 while moving left.
3. **Check the types.** Hover over `hi` in the editor: `usize`. The Java code depended on `-1`, which `usize` cannot hold.
4. **Do not patch the symptom.** `hi = mid.saturating_sub(1)` or `wrapping_sub` stops the panic but turns the termination condition into a bug: `0.saturating_sub(1)` is `0`, so `lo <= hi` stays true and the loop never ends. An early `if mid == 0 { break; }` works but leaves two special cases where the half-open form has none.

### Algorithm

1. Set `lo = 0` and `hi = release_times.len()`. Invariant: every index below `lo` is a release at or before `at`, and every index at or above `hi` is a release after `at`.
2. While `lo < hi`: let `mid = lo + (hi - lo) / 2`. If `release_times[mid] <= at`, set `lo = mid + 1`; otherwise set `hi = mid`.
3. Now `lo` is the number of releases at or before `at`. Return `lo - 1` as an `i32` (which is `-1` when `lo` is 0).

### Correctness

The invariant holds initially, since nothing is below 0 or at and above `len`. In each step `lo <= mid < hi`. If `release_times[mid] <= at`, then every index up to `mid` is at or before `at`, because the times increase, so `lo = mid + 1` keeps the invariant; otherwise every index from `mid` on is after `at`, so `hi = mid` keeps it. The range `[lo, hi)` shrinks by at least one each step, so the loop ends, with `lo == hi`. Then indexes below `lo` are at or before `at` and indexes from `lo` on are after it, so `lo - 1` is the last release at or before `at`, or `-1`. `hi - lo` is computed only while `lo < hi`, and `hi` is only ever assigned `mid`, never `mid - 1`, so no `usize` arithmetic can underflow. `lo` is at most 10^5, so the cast to `i32` is exact.

### Complexity

- Time: O(log n) — the range halves on every step.
- Space: O(1) — three indexes.

### Trade-offs

The half-open loop is the idiomatic Rust binary search, and it is exactly what the standard library offers: `release_times.partition_point(|&t| t <= at) as i32 - 1` is a one-line equivalent and the best production answer. `binary_search` is less suited here: it returns `Ok` with *any* matching index or `Err` with the insertion point, so the answer needs a `match`. Keeping the closed interval with signed `i64` bounds (`hi = len as i64 - 1`, casting `mid` back to `usize` to index) also works and mirrors the Java code, at the cost of casts on every access.

### Pitfalls and edge cases

- The general trap: `usize` cannot be negative. `len() - 1`, `i - 1` and `hi - lo` panic with overflow checks on and wrap to huge values with them off. An algorithm that relies on an index reaching `-1` needs a different invariant, or signed arithmetic.
- `for i in 0..v.len() - 1` panics on an empty vector for the same reason; `for i in 1..v.len()` or `v.windows(2)` does not.
- `saturating_sub(1)` hides the panic but breaks the loop's termination, as described above.
- Debug and release builds fail differently: a panic at the subtraction in one, an out-of-bounds index (or, for code that does not index, a silently wrong answer) in the other. Test with overflow checks on.

### Prevention

- Prefer half-open ranges (`start..end`) for indexes, which is how Rust's slices, iterators and standard search methods are designed.
- Use `partition_point`, `binary_search_by` and iterator adapters instead of hand-written index arithmetic.
- Enable `overflow-checks = true` in the release profile of services where a wrong answer is worse than a crash, and keep debug-build tests in CI.
- Clippy's `clippy::arithmetic_side_effects` (restriction group) flags unchecked arithmetic; it is noisy for general code but useful in index-heavy modules.

### Language notes

- Rust only. Java, Kotlin and Go index with signed integers, so `hi = -1` is an ordinary value and the closed-interval search is correct there. Python and TypeScript have no fixed-width integers at all.
- `usize` arithmetic follows the same rules as every integer type in Rust: checked in debug builds, wrapping in release builds, unless the profile sets `overflow-checks`. `checked_sub` returns an `Option`, `wrapping_sub` and `saturating_sub` make the choice explicit.
