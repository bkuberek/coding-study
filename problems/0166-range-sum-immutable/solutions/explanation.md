# Range Sum Query: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-range | brute | O(n) per sumRange | O(1) | only a handful of queries, or as a correctness oracle |
| prefix-sums | optimal | O(1) per sumRange, O(n) to build | O(n) | default answer whenever the array is fixed |

`n` is the length of `nums`. The generated sequences make as many `sumRange` calls as there are elements, so the brute force costs O(n^2) per sequence and prefix sums O(n).

## Approach: scan-range (Add up the range on every query)

### Intuition

The question asks for a sum, so compute it: walk from `left` to `right` and add every value. Nothing is precomputed, which keeps the class trivial.

### Algorithm

1. The constructor keeps a reference to `nums`.
2. `sumRange(left, right)`: start a 64-bit total at 0, add `nums[i]` for every `i` from `left` to `right`, and return the total.

### Correctness

The loop visits exactly the positions `left`, `left + 1`, ..., `right`, once each, so the total is the definition of the range sum. The array never changes, so every call sees the same values.

### Complexity

- Time: O(n) per sumRange — a range can span the whole array; with random ranges it spans a third of it on average, so n calls cost O(n^2).
- Space: O(1) — the class keeps a reference to the caller's array, not a copy, and each call needs a single accumulator.

### Trade-offs

Simplest possible code and no preparation cost, so it wins when there are only one or two queries. As soon as queries repeat over the same array it does the same additions again and again, which is exactly what prefix sums avoid.

### Pitfalls and edge cases

- `right` is inclusive: the loop runs to `right`, and a Python slice must end at `right + 1`.
- A range of 10^5 values of 10^5 adds up to 10^10, which overflows a 32-bit accumulator. Use a `long` total in Java and Kotlin.

### Language notes

- Python: `sum(self.nums[left : right + 1])` copies the slice and adds it in C; still O(n) per call.
- Kotlin: `left..right` is an inclusive range, matching the problem's bounds.

## Approach: prefix-sums (Prefix sums built once)

### Intuition

Every range sum is the difference of two "sums so far". If `prefix[i]` is the total of the first `i` values, then the values from `left` to `right` are the first `right + 1` values minus the first `left` values. Computing all prefixes takes one pass, after which every query is a subtraction.

### Algorithm

1. Allocate `prefix` with `n + 1` entries and set `prefix[0] = 0`.
2. For `i` from 0 to `n - 1`: `prefix[i + 1] = prefix[i] + nums[i]`.
3. `sumRange(left, right)` returns `prefix[right + 1] - prefix[left]`.

### Correctness

By induction on `i`, `prefix[i]` equals `nums[0] + ... + nums[i - 1]`: it holds for `i = 0` (the empty sum), and step 2 extends a correct prefix by one value. Then `prefix[right + 1] - prefix[left]` removes the common first `left` terms and leaves exactly `nums[left] + ... + nums[right]`.

### Complexity

- Time: O(1) per sumRange, O(n) to build — the constructor makes one pass; each query reads two entries and subtracts.
- Space: O(n) — the `n + 1` prefix totals.

### Trade-offs

The standard answer: a linear preparation pays for itself after a couple of queries. It relies on the array being immutable; a single update would force rebuilding O(n) prefixes, which is where a Fenwick tree or segment tree takes over (Range Sum Query With Updates).

### Pitfalls and edge cases

- The extra leading 0 is what makes `left = 0` work without a special case; without it you would read `prefix[-1]`.
- The prefixes reach 10^10 in absolute value, so they must be 64-bit (`long[]`, `LongArray`); in Java and Kotlin, `prefix[i] + nums[i]` widens the `int` automatically because the left operand is a `long`.
- Off-by-one: the answer uses `right + 1`, not `right`.

### Language notes

- Python: `itertools.accumulate(nums, initial=0)` yields `0` followed by the running totals, exactly the prefix array; Python integers never overflow.
- TypeScript: plain `number` arithmetic is exact for integers up to 2^53, and these sums stay far below it, so no `BigInt` is needed.
- Java: `long[]` prefixes; the subtraction of two `long` values returns `long`, matching the signature.
- Kotlin: `LongArray(nums.size + 1)` starts zero-filled, so `prefix[0] = 0` comes for free; the `init` block fills it.
