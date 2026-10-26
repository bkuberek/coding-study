# Missing Number: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-and-scan | brute | O(n log n) | O(n) | the array is sorted anyway, or as a correctness oracle |
| expected-sum | optimal | O(n) | O(1) | quickest to explain; mind the overflow in fixed-width languages |
| xor-indices | optimal | O(n) | O(1) | default when you want no overflow question at all |

Both optimal approaches compare the array with the full set `0..n`, which is known without looking at the input: once with addition, once with XOR. A hash set of the values also works in O(n) time but needs O(n) memory.

## Approach: sort-and-scan (Sort and find the first gap)

### Intuition

In sorted order, the numbers `0, 1, 2, ...` sit at their own indexes until the gap: the first index whose value differs from it is the missing number. If there is no such index, the missing number is `n`.

### Algorithm

1. Sort a copy of `nums`.
2. Return the first index `i` with `sorted[i] != i`.
3. If every index matches, return `n`.

### Correctness

Let `m` be the missing number. The values below `m` are exactly `0..m-1`, so in sorted order they fill indexes `0..m-1` with `sorted[i] = i`. Index `m` holds the next present value, `m + 1`, which differs from `m`. If `m = n`, the array is exactly `0..n-1` and every index matches.

### Complexity

- Time: O(n log n) — the sort dominates the linear scan.
- Space: O(n) — the sorted copy (sorting in place would need O(1) extra, but mutates the input).

### Trade-offs

Easy to reason about, and linear if the input happens to be sorted already (then binary search even finds the gap in O(log n)). Otherwise the sort is wasted work compared with one pass.

### Pitfalls and edge cases

- Do not forget the case `m = n`: no index mismatches.
- In TypeScript, `[...].sort()` without a comparator sorts as strings (`10` before `9`); the reference sorts an `Int32Array`, which compares numerically.

## Approach: expected-sum (Subtract the sum from the sum of 0 to n)

### Intuition

The full set `0..n` adds up to `n(n + 1)/2`. The array holds the same numbers except one, so the difference between the two sums is exactly the missing number.

### Algorithm

1. Compute `expected = n * (n + 1) / 2` in 64-bit arithmetic.
2. Subtract every value of `nums`.
3. Return the difference.

### Correctness

`sum(0..n) = n(n + 1)/2` by Gauss's formula, and `sum(nums) = sum(0..n) - m` because `nums` contains every number of `0..n` except `m`, once each. Subtracting gives `m`.

### Complexity

- Time: O(n) — one pass to subtract.
- Space: O(1) — one accumulator.

### Trade-offs

Very short and easy to justify. Its weak spot is the magnitude: for `n = 10^5` the sum is about `5 * 10^9`, beyond a 32-bit `int`. In Java and Kotlin, computing `n * (n + 1)` in `int` overflows before the division by 2, which breaks the result; wrapping arithmetic alone would be harmless here, because the true answer fits in 32 bits, but the division is not compatible with wrapping. Using 64 bits avoids the issue.

### Pitfalls and edge cases

- Compute `n * (n + 1)` in `long` (Java) or `Long` (Kotlin), not in `int`.
- Use integer division, `//` in Python; `/` would produce a float.

### Language notes

- Python: integers are unbounded, so `n * (n + 1) // 2 - sum(nums)` is exact.
- TypeScript: numbers are doubles, exact up to 2^53, so `5 * 10^9` is no problem.
- Java: `long n = nums.length` makes the whole expression 64-bit; the final cast to `int` is safe because the answer is at most `n`.
- Kotlin: `nums.sumOf { it.toLong() }` sums in 64 bits.

## Approach: xor-indices (XOR every index and value together)

### Intuition

XOR cancels equal values: `a ^ a = 0`. If you XOR together all numbers `0..n` and all values of the array, every present number appears twice and cancels, leaving only the missing one. The indexes `0..n-1` plus `n` itself are exactly the full set, so one loop over the array covers both.

### Algorithm

1. Start with `result = n`.
2. For every index `i`: `result ^= i ^ nums[i]`.
3. Return `result`.

### Correctness

After the loop, `result` is the XOR of `0, 1, ..., n` (the initial `n` plus the indexes) and of all values in `nums`. XOR is commutative and associative, so pair each present number from the first group with its copy in the second; each pair contributes 0. The only unpaired number is `m`, so `result = m`.

### Complexity

- Time: O(n) — one pass.
- Space: O(1) — one accumulator.

### Trade-offs

Same cost as the sum, but no intermediate value ever exceeds the largest number involved (about `2^17` here), so there is no overflow to discuss in any language. It is slightly less obvious to explain than the sum.

### Pitfalls and edge cases

- Include `n` itself: the indexes only go up to `n - 1`. Starting `result` at `n` is the simplest way.
- Duplicate values would break the cancellation; the constraints rule them out.

### Language notes

- Python, TypeScript and Java use `^`; Kotlin uses the infix function `xor`. All values are small non-negative integers, so 32-bit XOR (TypeScript, JVM) and unbounded XOR (Python) agree.
