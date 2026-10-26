# Single Number: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| count-occurrences | brute | O(n) | O(n) | the counts are needed anyway, or values may occur other than twice |
| xor-fold | optimal | O(n) | O(1) | default answer |

Both are linear; the bit trick removes the memory. It depends on the exact promise of the problem (every other value occurs exactly twice), while counting works for any multiplicities.

## Approach: count-occurrences (Count every value in a hash map)

### Intuition

Count how often each value occurs, then return the one whose count is 1.

### Algorithm

1. Build a map from value to count in one pass.
2. Return the value whose count is 1.

### Correctness

After the first pass, every value's count is its number of occurrences. By the promise, exactly one value has count 1, and step 2 returns it.

### Complexity

- Time: O(n) — one pass to count and one pass over at most (n + 1) / 2 distinct values, with O(1) average map operations.
- Space: O(n) — one entry per distinct value.

### Trade-offs

Simple, general (it works for "every other value occurs three times" without change) and a solid first answer. The follow-up asks for O(1) memory, which a map cannot give.

### Pitfalls and edge cases

- Do not stop at the first count of 1 during the counting pass: the second copy of that value may come later.
- Sorting and then scanning pairs also works with O(1) extra memory (if sorting in place is allowed), at O(n log n) time.

## Approach: xor-fold (XOR all the values together)

### Intuition

Exclusive or works bit by bit: each output bit is 1 when an odd number of the inputs have a 1 there. A value XORed with itself is 0, XOR with 0 changes nothing, and the order does not matter. So XORing the whole array cancels every pair and leaves exactly the lonely value.

### Algorithm

1. Start with `result = 0`.
2. For each value, set `result = result ^ value`.
3. Return `result`.

### Correctness

XOR is commutative and associative, so the result equals the XOR of the values in any order, for example with each pair adjacent: `(a ^ a) ^ (b ^ b) ^ ... ^ s = 0 ^ 0 ^ ... ^ s = s`. Per bit position: each paired value contributes its bit twice, an even count, so only the lonely value's bit decides the parity.

### Complexity

- Time: O(n) — one XOR per value.
- Space: O(1) — one accumulator.

### Trade-offs

Optimal in time and memory and very short, which is why interviewers like it. It relies entirely on the "exactly twice" promise: with a value occurring three times, plain XOR fails, and the generalization counts bits modulo 3 instead.

### Pitfalls and edge cases

- Negative values need no special handling: two's complement XOR treats the sign bit like any other bit.
- Starting from anything other than 0 corrupts the result.
- An input violating the promise (some value occurring three times) silently produces a wrong answer; XOR cannot detect it.

### Language notes

- Python: integers are unbounded, but XOR behaves as if they had infinitely many copies of the sign bit, so `-2 ^ -2 == 0` and a negative lonely value comes out negative; `functools.reduce(operator.xor, nums, 0)` folds the array.
- TypeScript: `^` first converts both operands to 32-bit signed integers. Every input here is a 32-bit integer, so nothing is lost; with values beyond 32 bits it would silently truncate.
- Java: `int` is 32-bit two's complement, matching the inputs exactly.
- Kotlin: there is no `^` operator; the infix function `xor` does the same (`result xor value`), and `fold(0)` accumulates over the `IntArray`.
