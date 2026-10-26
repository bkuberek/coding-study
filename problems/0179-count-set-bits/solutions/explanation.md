# Count Set Bits: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| check-every-bit | brute | O(32) | O(1) | the obvious first answer; constant time per word |
| clear-lowest-bit | optimal | O(k) | O(1) | sparse words; the classic interview trick |

`k` is the number of set bits, at most 32. Both are constant time for a fixed word size; the trick spends one step per set bit instead of one per position. In production code the built-ins (`Integer.bitCount`, `Long.bitCount`, `countOneBits`, `int.bit_count`) compile to a single CPU instruction on most machines.

The input is an unsigned 32-bit value, which no signature type here can hold directly except a 64-bit integer: Java's and Kotlin's `int` and TypeScript's bitwise operators are 32-bit signed, so `2^32 - 1` would read as `-1`. The references therefore take a `long` (a `number` in TypeScript) and either work on it directly or narrow it to its low 32 bits, which have the same set bits.

## Approach: check-every-bit (Test each of the 32 bit positions)

### Intuition

A 32-bit word has 32 positions. Shift the word right by each position and look at the lowest bit; add up the ones.

### Algorithm

1. For each position `p` from 0 to 31, add `(n >> p) & 1` to the count.
2. Return the count.

### Correctness

`(n >> p) & 1` is exactly bit `p` of `n` (the bits shifted out on the right are gone, and the mask keeps only the new lowest bit). Summing it over every position counts every 1 bit once; since `n < 2^32`, no bit above position 31 is set.

### Complexity

- Time: O(32) — always 32 shifts and masks, whatever the value: constant time.
- Space: O(1) — a counter.

### Trade-offs

Simple and branch-free, with a fixed cost. When most bits are 0, it wastes steps on positions that contribute nothing; the next approach skips them.

### Pitfalls and edge cases

- Shifting a signed 32-bit value right with `>>` copies the sign bit into the top, so a loop of the form `while (n != 0) { ...; n >>= 1; }` never ends for negative inputs. Use an unsigned shift (`>>>` in Java and TypeScript, `ushr` in Kotlin) or a fixed loop of 32 steps.
- Do not stop at the highest set bit by testing `n > 0` on a signed narrow value: values from `2^31` up are negative there.

### Language notes

- TypeScript: `n >>> p` converts `n` to an unsigned 32-bit integer first, so the top bit of `2^32 - 1` is read correctly; `n >> p` would treat it as a sign.
- Java: on a `long`, `>>>` and `>>` agree because the value is non-negative; `(int) (... & 1L)` narrows the bit to an `int`.
- Kotlin: shifts and masks are infix functions on `Long`: `(n ushr p) and 1L`.

## Approach: clear-lowest-bit (Clear the lowest set bit until none is left)

### Intuition

Subtracting 1 from a number flips its lowest set bit to 0 and every 0 below it to 1, leaving the higher bits alone. So `n & (n - 1)` keeps the higher bits and clears exactly the lowest set bit. Repeating that until the word is 0 takes one step per set bit.

### Algorithm

1. Set `count = 0`.
2. While `n` is not 0: replace `n` with `n & (n - 1)` and increment `count`.
3. Return `count`.

### Correctness

Write `n` as `h 1 0...0`, where `h` is the higher bits and the shown `1` is the lowest set bit followed by `t` zeros. Then `n - 1 = h 0 1...1`, and `n & (n - 1) = h 0 0...0`: exactly one set bit fewer. Each iteration removes one set bit and the loop stops at 0, so it runs once per set bit.

### Complexity

- Time: O(k) — one iteration per set bit, at most 32.
- Space: O(1) — a counter.

### Trade-offs

Faster than checking every position on sparse words and a frequent interview question in its own right; the identity `n & (n - 1)` also tests for powers of two (`n & (n - 1) == 0` for `n > 0`). For dense words it does about the same work as the fixed loop. A 256-entry table of byte popcounts handles a word in 4 lookups, and the built-in instruction beats both.

### Pitfalls and edge cases

- `n = 0` must return 0 without entering the loop.
- On 32-bit signed integers, the step from `-2^31` (only the top bit set) computes `-2^31 - 1`, which overflows. In Java and Kotlin `int` arithmetic wraps to `2^31 - 1` and the AND gives 0, exactly the right bits; in TypeScript the double `-2^31 - 1` is converted back to the 32-bit value `2^31 - 1` by `&`, with the same result.

### Language notes

- Python: integers are unbounded and non-negative here, so `n &= n - 1` works directly; `int.bit_count()` (Python 3.10+) is the built-in.
- TypeScript: `n | 0` brings the value into 32-bit signed range (the same 32 bits); the loop condition `!== 0` works for negative words too.
- Java: `(int) n` keeps the low 32 bits; `Integer.bitCount(word)` or `Long.bitCount(n)` is the built-in.
- Kotlin: `n.toInt()` narrows the same way; `and` replaces `&`, and `countOneBits()` is the built-in.
