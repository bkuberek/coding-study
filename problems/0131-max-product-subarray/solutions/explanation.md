# Maximum Product Subarray: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness baseline |
| track-min-max | optimal | O(n) | O(1) | default answer: the dynamic-programming view |
| prefix-suffix | optimal | O(n) | O(1) | you prefer a structural argument over a recurrence |

Every non-zero value here has absolute value at least 1, so inside a run without zeros, extending a subarray never makes its absolute product smaller; only the sign is in question. That fact drives both linear solutions.

## Approach: brute-force (Extend a product from every start)

### Intuition

Every subarray has a first element. Fixing it and extending one element at a time gives the product of each longer subarray from the previous one in O(1), so all n(n + 1) / 2 products cost quadratic time, with no need to recompute any product from scratch.

### Algorithm

1. Set `best = nums[0]`.
2. For each `start`, set `product = 1`; for each `end >= start`, multiply `product` by `nums[end]` and update `best`.
3. Return `best`.

### Correctness

Each pair `start <= end` is visited exactly once, and at that moment `product` equals the product of `nums[start..end]`. So `best` is the maximum over all non-empty subarrays. Starting `best` at `nums[0]` instead of 0 matters when every product is negative.

### Complexity

- Time: O(n^2) — n(n + 1) / 2 multiplications and comparisons.
- Space: O(1) — a running product and the best value.

### Trade-offs

Obviously correct and short, which makes it the oracle; too slow for 2 * 10^4 elements in Python, where it would take about 2 * 10^8 steps.

### Pitfalls and edge cases

- Do not start `best` at 0: for `[-7]` the answer is -7.
- Recomputing each product from scratch (a third loop) makes it O(n^3).
- Slicing the array (`nums[start:]` in Python) copies it, which adds O(n) memory per start; index instead.

### Language notes

- All four languages use the same two nested index loops; the products of real subarrays fit in 32 bits by the constraints, so Java and Kotlin `int` never overflow.

## Approach: track-min-max (Largest and smallest product ending at each index)

### Intuition

Kadane's algorithm for sums keeps only the best sum ending at each position. Products break that: a large negative product ending at `i - 1` becomes a large positive one when `nums[i]` is negative. So keep two values per position, the largest and the smallest product of a subarray ending there. The subarray ending at `i` is either `nums[i]` alone, or it extends the subarray ending at `i - 1`, and then its product is `nums[i]` times one of those two extremes.

State: `largest[i]` and `smallest[i]`, the maximum and minimum products over subarrays ending at `i`. Recurrence: both are the maximum and minimum of `nums[i]`, `largest[i - 1] * nums[i]` and `smallest[i - 1] * nums[i]`. A table version stores the two arrays; since each position reads only the previous one, the reference keeps two variables.

### Algorithm

1. Set `largest = smallest = best = nums[0]`.
2. For each later `value`: compute the three candidates `value`, `largest * value`, `smallest * value`; set `largest` to their maximum and `smallest` to their minimum (from the old values); update `best` with `largest`.
3. Return `best`.

### Correctness

Invariant: after index `i`, `largest` and `smallest` are the maximum and minimum products of subarrays ending at `i`. A subarray ending at `i` is `[nums[i]]` or `X` followed by `nums[i]`, with `X` ending at `i - 1`. Multiplying by `nums[i]` is monotonic over the products of all such `X` (increasing when `nums[i] >= 0`, decreasing otherwise), so the extremes of the extended products come from the extremes of `X`, which are `largest` and `smallest` by the invariant. Every subarray ends somewhere, so `best` sees the overall maximum.

### Complexity

- Time: O(n) — three multiplications and a few comparisons per element.
- Space: O(1) — three variables.

### Trade-offs

The expected interview answer: one pass, constant memory, and the reasoning generalizes to other "sign flips the order" problems. The subtle part is updating both extremes from the old values.

### Pitfalls and edge cases

- Compute both candidates before assigning either variable; updating `largest` first and then using it for `smallest` is the classic bug.
- Zeros need no special case: `value` itself (0) becomes both extremes, and the next element restarts from it.
- Each candidate is the product of a real subarray, so it fits in 32 bits; no intermediate overflow is possible.

### Language notes

- Python: a tuple of candidates feeds both `max` and `min`.
- TypeScript: `Math.max` and `Math.min` take any number of arguments. A product such as `0 * -3` is `-0`, which compares equal to 0 and serializes as `0`.
- Java: nested `Math.max` calls, since it takes exactly two arguments.
- Kotlin: `maxOf` and `minOf` take three arguments directly.

## Approach: prefix-suffix (Best running product from the left and from the right)

### Intuition

Split the array at its zeros. Within a zero-free run, take the whole run if it has an even number of negative values. If the count is odd, the best product drops everything up to and including the first negative, or everything from the last negative on; what remains is a suffix or a prefix of the run. Running products from the left and from the right, restarted after every zero, pass through every prefix and suffix of every run.

### Algorithm

1. Set `best` to the maximum element (this covers zeros and single negative elements).
2. Keep `fromLeft` and `fromRight`, both starting at 1. For each `i`, if a running product is 0, restart it at 1; then multiply `fromLeft` by `nums[i]` and `fromRight` by `nums[n - 1 - i]`, and update `best` with both.
3. Return `best`.

### Correctness

Take an optimal subarray. If its product is positive or zero it either is a single element or lies inside a zero-free run (or the answer is 0, covered by step 1 when a zero exists). Inside a run with an even number of negatives, the whole run is at least as good as any part of it, because absolute values are at least 1; the left scan reaches the whole run as a prefix. With an odd number, any subarray containing both the first and the last negative of the run has a negative product, so a positive optimum lies entirely after the first negative or entirely before the last one; extending it to the end or the start of the run (without crossing that negative) keeps the sign and does not shrink the absolute value. Those extended subarrays are a suffix and a prefix of the run, seen by the right and left scans. If the optimum is negative, it is a single element (otherwise dropping an end element would not decrease it), covered by step 1.

### Complexity

- Time: O(n) — one pass, two multiplications per index.
- Space: O(1) — two running products and the best value.

### Trade-offs

Equally fast and arguably simpler code than tracking the minimum, but its correctness argument is structural rather than a recurrence, which is harder to state under pressure. Good as a second answer that shows depth.

### Pitfalls and edge cases

- Restart after a zero by treating the running product as 1 before multiplying; otherwise every later product stays 0.
- The initial `best` must include every element (or at least the zeros); a running product never "sees" the zero itself as a candidate after restarting.

### Language notes

- Python: `(from_left or 1)` restarts a zero product in one expression.
- TypeScript: `Math.max(...nums)` spreads up to 2 * 10^4 arguments, well inside the engine's limit; `fromLeft === 0` is also true for `-0`.
- Java: `Arrays.stream(nums).max().getAsInt()` computes the initial best.
- Kotlin: `nums.max()` on an `IntArray` returns the maximum and throws only on an empty array, which the constraints rule out.
