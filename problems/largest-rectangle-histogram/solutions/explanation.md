# Largest Rectangle in Histogram: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | small histograms, or as a correctness oracle |
| monotonic-stack | optimal | O(n) | O(n) | default answer |

The best rectangle always has the height of its lowest bar, and it cannot be widened past a lower bar on either side. So for each bar used as the height, the best rectangle reaches from just after the nearest lower bar on the left to just before the nearest lower bar on the right. The brute force tries every range directly; the stack finds both boundaries for every bar in one pass.

## Approach: brute-force (Fix the left bar and extend with a running minimum)

### Intuition

For a fixed range of bars, the tallest rectangle inside it is as high as its lowest bar. Fix the left end, move the right end outwards one bar at a time, and keep the running minimum: every range costs O(1).

### Algorithm

1. Set `best = 0`.
2. For each `left`, set `lowest = heights[left]`; for each `right` from `left` to `n - 1`:
   1. `lowest = min(lowest, heights[right])`.
   2. `best = max(best, lowest * (right - left + 1))`.
3. Return `best`.

### Correctness

Any rectangle inside the histogram covers some range `left..right` and is at most as tall as the lowest bar there, so its area is at most `lowest * (right - left + 1)` for that range, a value the loops compute. That value is achievable, so `best` is the maximum over all rectangles.

### Complexity

- Time: O(n^2) — n (n + 1) / 2 ranges, O(1) each.
- Space: O(1) — the running minimum and the best area.

### Trade-offs

Correct by construction, which makes it the oracle; at 5,000 bars it already takes about 1.25 * 10^7 steps. Expanding left and right from every bar while the neighbors are at least as high is a common alternative brute force; it is just as quadratic on a staircase.

### Pitfalls and edge cases

- Bars of height 0 give area 0, and a histogram of zeros has answer 0.
- The largest area is at most 10^5 * 10^4 = 10^9, which fits in a 32-bit signed integer.

### Language notes

- The four references are the same two nested loops; `Math.min`/`Math.max` in TypeScript and Java, `minOf`/`maxOf` in Kotlin, `min`/`max` in Python.
- Go: the built-in `min` and `max` (Go 1.21 and newer) replace helper functions; areas stay below 10^9, well inside `int`.
- Rust: `heights[left..].iter().enumerate()` yields each right bar with its offset, so the width is `offset + 1`. The largest area is 10^4 * 10^5 = 10^9, which fits `i32`.

## Approach: monotonic-stack (Stack of bars with increasing heights)

### Intuition

Walk the bars left to right and keep a stack of bar indexes whose heights increase from bottom to top. These are the bars whose rectangle can still grow to the right. When a bar arrives that is not higher than the top, the top bar's rectangle cannot extend any further right: the new bar is its right boundary. Its left boundary is the bar just below it on the stack, which is lower. Pop it, record `height * (right - left - 1)`, and repeat. A final bar of height 0 flushes the stack.

### Algorithm

1. For `index` from 0 to `n` (with height 0 at `index = n`):
   1. While the stack is not empty and the bar on top is at least as high as the current height, pop `top`; let `left` be the new top, or -1; update `best` with `heights[top] * (index - left - 1)`.
   2. Push `index`.
2. Return `best`.

### Correctness

Stack invariant: heights strictly increase from bottom to top, and the bar below each entry is the nearest bar to its left that is strictly lower (bars between them were popped by bars no higher than they were, so all of them are at least as high as the entry).

When `top` is popped by `index`, every bar between `left` and `index` is at least `heights[top]`, so the rectangle of height `heights[top]` over `(left, index)` fits. If `heights[index] < heights[top]`, this is the widest rectangle with that bar as the lowest bar. If they are equal, the popped bar's rectangle may be too narrow, but the equal bar at `index` stays on the stack with the same `left` boundary (it inherits it, since `top` is gone), and when it is popped later its rectangle covers the full width. So for every bar, the widest rectangle with that bar's height is recorded at some pop, and the best rectangle overall is the widest one for its lowest bar.

### Complexity

- Time: O(n) — each index is pushed once and popped once.
- Space: O(n) — on an ascending staircase every bar is on the stack at the end.

### Trade-offs

Linear, and the standard answer for this hard problem. A two-pass variant computes "nearest lower on the left" and "nearest lower on the right" into two arrays and then takes the best `height * width`; it is easier to reason about but uses two extra arrays. A divide-and-conquer solution (split at the lowest bar) runs in O(n log n) on average with a segment tree for range minimums, and O(n^2) in the worst case without one.

### Pitfalls and edge cases

- Width is `index - left - 1`, with `left = -1` when the stack is empty; forgetting the `- 1` overcounts by one bar.
- Without the sentinel bar, bars left on the stack at the end are never measured (an ascending histogram would return 0).
- With equal heights, popping on `>=` or on `>` both work, but the argument for each differs; the references pop on `>=`.

### Language notes

- Python: a list as the stack; `rising[-1]` reads the top.
- TypeScript: an array with `push`/`pop`; `pop()!` is safe inside the non-empty loop.
- Java: a primitive `int[]` with a size counter, sized `n + 1` for the sentinel step.
- Kotlin: `ArrayDeque<Int>` with `lastOrNull() ?: -1` for the left boundary.
- Go: the sentinel bar is a conditional (`height := 0; if index < len(heights) { ... }`), since Go has no conditional expression. The left boundary is `-1` when the stack is empty.
- Rust: `heights.get(index).copied().unwrap_or(0)` supplies the sentinel bar. The rectangle starts one bar after the bar below `top` (or at 0), so with `usize` indexes no `-1` is needed.
