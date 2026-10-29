# Max Consecutive Ones With K Flips: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| sliding-window | optimal | O(n) | O(1) | default answer; the window is always valid |
| steady-window | optimal | O(n) | O(1) | only the length is needed; shortest code |

Every approach uses the same reformulation: the answer is the longest window with at most `k` zeros, because flipping the zeros of such a window makes it all ones, and flipping zeros outside it does not lengthen it.

## Approach: brute-force (Extend from every start while flips remain)

### Intuition

From each start, walk right and spend one flip per zero. Stop at the zero that would need flip number `k + 1`. The walk length is the longest valid window with that start.

### Algorithm

1. Set `best = 0`.
2. For each `start`: set `zeros = 0` and walk `end` from `start`; at a zero, stop if `zeros == k`, otherwise count it. Update `best` with `end - start`.
3. Return `best`.

### Correctness

For a fixed start, the zero count of `nums[start .. end]` never decreases as `end` grows, so the first zero that exceeds the budget ends every valid window with this start. The walk therefore measures the longest valid window for each start, and every window has a start.

### Complexity

- Time: O(n^2) — each start can walk to the end. The generator sizes `k` so that windows span n/16 to n/8 positions, so the walks stay long at every seed.
- Space: O(1) — two counters.

### Trade-offs

Direct and obviously correct, hence the oracle. Consecutive starts share almost all of their walks; a sliding window keeps the shared part.

### Pitfalls and edge cases

- With `k = 0` the walk stops at the first zero, so a start on a zero yields length 0; the answer is the longest run of ones, or 0 if there are none.
- `k >= number of zeros` gives the whole array.

### Language notes

- Python, TypeScript, Java, Kotlin: two nested loops over the array with an early exit; no allocation.
- Go: plain `int` counters and the builtin `max`; the inner loop stops at the first zero that would need one flip too many.
- Rust: `zeros` is compared with `k` as `i32`, while the run length `end - start` is a `usize` that converts to `i32` once at the return.

## Approach: sliding-window (Shrink when the window holds too many zeros)

### Intuition

Keep a window `[left, right]` and the number of zeros in it. Add `nums[right]`; while the window holds more than `k` zeros, drop elements from the left. The window is then the longest valid window ending at `right`.

### Algorithm

1. Set `left = 0`, `zeros = 0`, `best = 0`.
2. For each `right`: if `nums[right] == 0`, increase `zeros`. While `zeros > k`, if `nums[left] == 0` decrease `zeros`, then increase `left`. Update `best` with `right - left + 1`.
3. Return `best`.

### Correctness

Invariant: after step 2, `zeros` is the number of zeros in `nums[left .. right]`, it is at most `k`, and `left` is the smallest start with that property for this `right`. The loop removes elements only while the window is invalid, and stops as soon as it becomes valid, so no valid start is skipped. `left` never needs to move back: a start that was invalid for some `right` is invalid for every later `right` too, because extending a window cannot remove zeros. The maximum over all `right` is the answer.

### Complexity

- Time: O(n) — `right` advances n times and `left` at most n times in total.
- Space: O(1) — three integers.

### Trade-offs

The standard "longest window with at most k bad elements" template, also used by Longest Repeating Replacement and Fruit Into Baskets. The window is always valid, so it is easy to extend the code to return the window itself.

### Pitfalls and edge cases

- Shrink with `while`: the left edge may need to pass several ones before it drops a zero.
- Decrease `zeros` only when the element leaving the window is a zero.
- `k = 0` still works: the window collapses past every zero.

### Language notes

- Python: `enumerate` gives position and bit together.
- TypeScript: `nums[left++] === 0` tests the leaving element and advances the edge in one expression.
- Java: same idiom with `int[]`.
- Kotlin: `nums[left++]` works on `IntArray` as in Java.
- Go: a counter of zeros in the window, with the left edge advancing while it exceeds `k`.
- Rust: `zeros` and `k` are both `i32`, and the window size is written `right + 1 - left` because the shrink loop can step `left` one past `right` (an empty window when `k` is 0), where `right - left + 1` would underflow `usize` first.

## Approach: steady-window (A window that never shrinks)

### Intuition

Only the maximum length matters, so once a window of length `L` has been seen, shorter windows are uninteresting. Let the window grow by one at each step, and when it becomes invalid (more than `k` zeros), slide it right by one instead of shrinking it: drop exactly one element on the left. The window length never decreases and, at the end, equals the answer, so the result is `n - left`.

### Algorithm

1. Set `left = 0` and `flipsLeft = k`.
2. For each element: if it is a zero, decrease `flipsLeft`. If `flipsLeft < 0`, drop `nums[left]` (increase `flipsLeft` if it was a zero) and increase `left`.
3. Return `n - left`.

### Correctness

Claim: after processing position `right`, the window length `right - left + 1` equals the best answer within `nums[0 .. right]`. Suppose it holds for `right - 1` with best `L`. Adding `nums[right]` gives a window of length `L + 1` ending at `right`. If that window has at most `k` zeros, it is valid and the best grows to `L + 1`; `flipsLeft` is not negative, so the window stays. If it has more than `k` zeros, no valid window of length `L + 1` ends at `right`, and none ends earlier (by the hypothesis), so the best stays `L`; the step drops one element and the length returns to `L`. The test is exact because `flipsLeft` always equals `k` minus the number of zeros in the current window: `flipsLeft < 0` holds precisely when the window of length `L + 1` has too many zeros. Between steps the window of length `L` may itself be invalid, which is harmless because only its length is used.

### Complexity

- Time: O(n) — one pass, each step moving the left edge at most once.
- Space: O(1) — two integers.

### Trade-offs

Shortest code and one comparison per step. The window is not always valid (it may hold more than `k` zeros while it slides), so this version only yields the length, not the window. Explaining why it is correct takes longer than explaining `sliding-window`, which is the safer interview answer.

### Pitfalls and edge cases

- Use `if`, not `while`, for the slide; a `while` turns it back into the shrinking window, and then `n - left` is no longer the answer.
- Return `n - left`, not the final window's zero count or `right - left`.
- With all zeros and `k = 0`, every step slides, and the result is `n - n = 0`.

### Language notes

- Python: a single `for value in nums` loop; the index of the right edge is never needed.
- TypeScript: `for (const value of nums)` and `nums[left++]` keep the loop short.
- Java: the slide condition and the leaving element combine into `if (flipsLeft < 0 && nums[left++] == 0)`; `&&` short-circuits, so `left` moves only when sliding.
- Kotlin: the same short-circuit expression works with `&&`.
- Go: the window never shrinks; `left` advances only when the flip budget goes negative, and the answer is whatever distance remains to the end of the slice.
- Rust: `flips_left` is an `i32` that dips to -1 and comes back, so it must be signed. Because `left` moves at most once per step, `nums.len() - left` cannot underflow `usize`.
