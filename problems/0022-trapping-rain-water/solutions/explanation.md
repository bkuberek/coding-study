# Trapping Rain Water: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| prefix-max | intermediate | O(n) | O(n) | clearest linear solution; memory is not a concern |
| monotonic-stack | intermediate | O(n) | O(n) | the data arrives as a stream from left to right |
| two-pointers | optimal | O(n) | O(1) | default answer; constant memory |

Every approach rests on one fact: the water above bar `i` is `min(L[i], R[i]) - height[i]`, where `L[i]` is the tallest bar at or left of `i` and `R[i]` the tallest bar at or right of `i`. The approaches differ in how they obtain those two maxima.

## Approach: brute-force (Scan both sides of every bar)

### Intuition

Water above a bar rises until it would spill over the lower of the two highest walls around it. For each bar, find the highest bar on its left and on its right by scanning, and add the difference between the lower of the two and the bar itself.

### Algorithm

1. Set `water = 0`.
2. For each position `i`:
   1. Scan `height[0 .. i]` for its maximum `L`.
   2. Scan `height[i .. n-1]` for its maximum `R`.
   3. Add `min(L, R) - height[i]` to `water`.
3. Return `water`.

### Correctness

Including bar `i` itself in both scans makes `min(L, R) >= height[i]`, so each term is non-negative. Water above bar `i` is held exactly up to the lower of the highest walls on its two sides: higher water would flow over that wall toward the outside (each further bar on that side is no taller), and lower water would leave a dip that can still fill. Summing over all bars gives the total.

### Complexity

- Time: O(n^2) — each of the n bars scans the whole array once (its left part plus its right part).
- Space: O(1) — two running maxima.

### Trade-offs

The formula is the whole insight, and the brute force applies it literally, which makes it the oracle. Every bar repeats almost the same scans as its neighbor, about 10^8 steps at n = 10^4. All better solutions remove exactly that repetition.

### Pitfalls and edge cases

- Include bar `i` in both scans, or a bar taller than all its neighbors would get a negative amount of water.
- Bars at the two ends always get zero: one of the maxima is the bar itself.
- One or two bars hold nothing.
- The total is below n * 10^4 = 10^9, so a 32-bit integer suffices.

### Language notes

- Python: `max(height[:i + 1])` and `max(height[i:])` copy and scan slices in C. It is still O(n) per bar, about ten times faster than nested Python loops.
- TypeScript, Java, Kotlin: two inner loops per bar with `Math.max`, `maxOf` or the like; no allocation.

## Approach: prefix-max (Precompute the tallest bar on each side)

### Intuition

`L[i]` is a running maximum from the left, and `R[i]` a running maximum from the right. Each can be computed for all positions in one pass, so storing them in two arrays turns the formula into a third linear pass. This is a one-dimensional dynamic programming view: `L[i] = max(L[i-1], height[i])`.

### Algorithm

1. Fill `L[0] = height[0]` and `L[i] = max(L[i-1], height[i])` for `i` from 1 to n - 1.
2. Fill `R[n-1] = height[n-1]` and `R[i] = max(R[i+1], height[i])` for `i` from n - 2 down to 0.
3. Return the sum of `min(L[i], R[i]) - height[i]` over all `i`.

### Correctness

By induction, `L[i]` equals the maximum of `height[0 .. i]`: true for `i = 0`, and the maximum of a prefix one longer is the larger of the previous maximum and the new element. The same holds for `R`. Step 3 is then exactly the brute-force formula.

### Complexity

- Time: O(n) — three passes of n steps.
- Space: O(n) — the arrays `L` and `R`.

### Trade-offs

The easiest linear solution to explain and to get right, and the stepping stone to the two-pointer version. It spends 2n integers of memory, which the two-pointer approach shows is unnecessary.

### Pitfalls and edge cases

- Include the bar itself in both maxima (`L[i]` covers `height[0 .. i]`). With only the bars strictly to the left and right, a local peak gets a level below its own height, and the term goes negative unless you clamp it at zero.
- Iterate the right maxima from right to left; filling them left to right computes prefix maxima twice.
- A single bar works: both arrays hold that bar and the sum is 0.

### Language notes

- Python: `itertools.accumulate(height, max)` computes the running maximum in C; reversing, accumulating and reversing back gives `R`.
- TypeScript: `new Array<number>(n)` preallocates; filling with explicit loops avoids the overhead of `reduce`.
- Java: `int[]` arrays start at zero; the loops overwrite every slot.
- Kotlin: `IntArray(n)` for both maxima; `indices.sumOf { ... }` sums the water. Its result type follows the lambda, `Int` here.

## Approach: monotonic-stack (Fill basins with a stack of falling bars)

### Intuition

Instead of computing water per bar (a column), compute it per basin layer (a row). Keep a stack of positions whose heights are non-increasing from bottom to top: these are the walls still waiting for a taller bar on the right. When a bar taller than the top of the stack arrives, the top is the floor of a basin; the next position below it on the stack is the left wall and the new bar is the right wall. The water in that layer is its width times the height between the floor and the lower wall.

### Algorithm

1. Start with an empty stack `falling` and `water = 0`.
2. For each position `right`:
   1. While the stack is non-empty and `height[top] < height[right]`:
      1. Pop the top; its height is the `bottom` of a layer.
      2. If the stack is now empty, stop: there is no left wall.
      3. Let `left` be the new top. Add `(right - left - 1) * (min(height[left], height[right]) - bottom)` to `water`.
   2. Push `right`.
3. Return `water`.

### Correctness

The stack holds positions with non-increasing heights, and every position between two adjacent stack entries is no taller than the lower of them and has already been filled up to the level the stack entries imply. When a taller bar arrives, the popped floor lies between `left` and `right`, the cells strictly between them have been raised to `bottom` by earlier layers, and both walls are higher than `bottom`. So exactly `(right - left - 1) * (min(height[left], height[right]) - bottom)` new units are trapped in this layer. Every unit of water belongs to exactly one such layer, the one whose floor it sits on, so the sum is the total.

### Complexity

- Time: O(n) — every position is pushed once and popped at most once.
- Space: O(n) — the stack, which holds all positions on a falling terrain.

### Trade-offs

Same growth as `prefix-max`, but it processes bars strictly left to right, so it also works on a stream and never needs to look ahead. The layer-by-layer reasoning is harder to explain and to debug. It is worth knowing because the same stack pattern solves Largest Rectangle in Histogram and Daily Temperatures.

### Pitfalls and edge cases

- Pop while the top is strictly lower than the new bar. Using `<=` also works but turns equal-height walls into empty zero-height layers.
- When the pop empties the stack, stop without adding water: there is no left wall, as at the start of a rising terrain.
- The width is `right - left - 1`: the cells strictly between the walls.
- Push the current position after the while loop, whether or not anything was popped.

### Language notes

- Python: a list works as a stack (`append`, `pop`, `[-1]`).
- TypeScript: arrays have `push` and `pop`; the reference uses `falling.pop()!` because the loop condition already guarantees a non-empty stack.
- Java: `ArrayDeque<Integer>` is the recommended stack; `java.util.Stack` is synchronized and slower. `push`, `pop` and `peek` work on the head.
- Kotlin: `kotlin.collections.ArrayDeque` with `addLast`, `removeLast` and `last()`; it boxes positions like the Java version.

## Approach: two-pointers (Settle the side with the lower wall)

### Intuition

The water above a bar needs only the smaller of its two maxima. Walk inward from both ends, tracking `leftMax` (tallest bar seen from the left) and `rightMax` (tallest from the right). If `height[left] < height[right]`, then `R[left]`, the true right maximum of the left position, is at least `height[right]`, which already exceeds everything that bounds `leftMax`. So the level above `left` is `leftMax`, known now, without knowing `R[left]` exactly. The symmetric argument settles `right` otherwise. Each step settles one bar.

### Algorithm

1. Set `left = 0`, `right = n - 1`, `leftMax = rightMax = 0`, `water = 0`.
2. While `left < right`:
   1. If `height[left] < height[right]`: set `leftMax = max(leftMax, height[left])`, add `leftMax - height[left]`, increase `left`.
   2. Otherwise: set `rightMax = max(rightMax, height[right])`, add `rightMax - height[right]`, decrease `right`.
3. Return `water`.

### Correctness

Invariant: every bar outside `[left, right]` has been credited its exact water; `leftMax` is the maximum of `height[0 .. left-1]` and `rightMax` that of `height[right+1 .. n-1]`; and the taller of `height[left]` and `height[right]` is at least every bar outside `[left, right]`. The last part holds because a pointer only moves past a bar that is no taller than the bar at the other pointer, and that other bar stays.

Take the left branch, `height[left] < height[right]`. After the update, `leftMax` equals `L[left]`, and by the invariant `leftMax <= height[right] <= R[left]`. So the level above `left` is `min(L[left], R[left]) = leftMax`, and the credited amount is exact. The right branch is symmetric: there `height[left] >= height[right]`, so `rightMax <= height[left] <= L[right]`. When the pointers meet, the remaining bar is at least as tall as every other bar, so it holds no water.

### Complexity

- Time: O(n) — each step moves one pointer, n - 1 steps in total.
- Space: O(1) — two pointers and two maxima.

### Trade-offs

Optimal in both time and memory, and short. It is the expected final answer in an interview, but it is the hardest of the four to justify: be ready to explain why the lower side's level is already known. If the explanation stalls, `prefix-max` is the safer fallback and only costs memory.

### Pitfalls and edge cases

- Compare the bars `height[left]` and `height[right]` (or the two maxima; both variants are correct), and move the lower side. Moving the higher side credits water that may spill.
- Update the side's maximum before adding water, so the term is never negative.
- Equal heights may go to either side; the reference moves the right pointer.
- The loop ends at `left == right`: that last bar is the tallest bar of the terrain, as both sides stopped against it, so it holds nothing.

### Language notes

- Python: two `max` builtin calls per step; at 10^5 bars this takes a few milliseconds.
- TypeScript: all arithmetic stays in small integers, which V8 keeps unboxed.
- Java: `int` throughout; the total stays below 10^9, so no `long` is needed.
- Kotlin: `maxOf` on `Int` compiles to `Math.max`; no boxing on `IntArray`.
