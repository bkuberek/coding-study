# Daily Temperatures: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | the log is short, or as a correctness oracle |
| monotonic-stack | optimal | O(n) | O(n) | default answer |

Both approaches look for the "next greater element" of every position. The brute force searches for it separately for each day; the stack finds all of them in one left-to-right pass by answering a day at the moment its warmer day arrives.

## Approach: brute-force (Scan ahead for a warmer day)

### Intuition

The definition is a search: starting from the day after `i`, walk forward until a reading beats `temperatures[i]`. The distance walked is the answer, and running off the end means 0.

### Algorithm

1. Create `waits`, filled with 0.
2. For each day `i`, scan `j = i + 1, i + 2, ...` and stop at the first `j` with `temperatures[j] > temperatures[i]`; set `waits[i] = j - i`.
3. If the scan reaches the end, leave `waits[i]` at 0.
4. Return `waits`.

### Correctness

The scan for day `i` visits the later days in order and stops at the first one that is strictly warmer, so `j - i` is exactly the distance to the next warmer day. When no later day is warmer, the scan never stops early and the default 0 is the required answer.

### Complexity

- Time: O(n^2) — in the worst case (a long run of readings that never rise) each day scans to the end of the log, about n^2 / 2 comparisons.
- Space: O(1) — beyond the output array, only two loop indexes.

### Trade-offs

Trivially correct, which makes it the oracle, and fast when warmer days come soon (random weather). A cold spell of 10^4 days already costs about 5 * 10^7 comparisons, while the stack stays linear.

### Pitfalls and edge cases

- Use a strict comparison: an equal reading is not warmer.
- Stop at the first warmer day; continuing the scan would find a later one.
- The last day always gets 0.

### Language notes

- All four references use two nested index loops with `break`; Kotlin's `IntArray(days)` and Java's `new int[days]` start at 0, TypeScript needs `fill(0)`, and Python uses `[0] * days`.

## Approach: monotonic-stack (Stack of days still waiting for a warmer one)

### Intuition

Walk through the days in order and keep the days whose warmer day has not come yet. When a new reading arrives, it answers every waiting day that is colder than it. The waiting days never get warmer from the oldest to the newest: if a newer waiting day were warmer than an older one, it would have answered the older one when it arrived. So the coldest waiting days sit at the top of a stack, and the new reading only has to pop from the top while it beats what it sees.

### Algorithm

1. Create `waits`, filled with 0, and an empty stack of day indexes.
2. For each day `d` in order:
   1. While the stack is not empty and the reading of the day on top is strictly lower than `temperatures[d]`, pop that day `e` and set `waits[e] = d - e`.
   2. Push `d`.
3. Days left on the stack never see a warmer day; they keep 0. Return `waits`.

### Correctness

Invariant: after processing day `d`, the stack holds exactly the days up to `d` that have no strictly warmer day up to `d`, and their readings are non-increasing from bottom to top. When day `d` arrives, the days it pops are colder than it and had no warmer day before `d`, so `d` is their first warmer day and the recorded distance is right. The pop stops at a day at least as warm as `d`; every day below it is at least as warm too (non-increasing order), so none of them is answered by `d`, which is correct. Pushing `d` on top keeps the order non-increasing, because everything colder than `d` was removed.

### Complexity

- Time: O(n) — every day is pushed once and popped at most once, so the inner loop runs at most n times over the whole pass.
- Space: O(n) — the stack holds every day of a run that never rises, up to the whole log.

### Trade-offs

Linear and short; it is the expected interview answer and the template for every "next greater element" problem. A right-to-left alternative reuses `waits` to jump ahead (from day `i`, jump to `i + 1`, then by `waits[i + 1]`, and so on) and needs no extra stack, but its amortized analysis is harder to explain.

### Pitfalls and edge cases

- Store indexes, not temperatures: the answer is a distance, and the reading is read back through the index.
- Pop while the top is strictly colder; popping equal readings would give an equal day as the answer.
- Days left on the stack at the end need no work only because `waits` starts at 0.

### Language notes

- Python: a list is the stack (`append`, `pop`, `waiting[-1]`).
- TypeScript: an array with `push` and `pop`; `pop()!` asserts that the stack is not empty, which the loop condition guarantees.
- Java: a plain `int[]` with a size counter avoids boxing every index into an `Integer`, as `ArrayDeque<Integer>` would.
- Kotlin: `ArrayDeque<Int>` with `addLast`, `removeLast` and `last()`; `withIndex()` gives the day and its reading together.
