# Sum Without Arithmetic Operators: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ripple-carry | brute | O(32) | O(1) | you want to mirror a hardware adder one column at a time |
| xor-and-carry | optimal | O(32) | O(1) | default answer; usually far fewer than 32 rounds |

Both are constant time for 32-bit words. The ripple adder always processes 32 columns; the XOR-and-carry loop processes all columns in parallel and repeats only as long as some carry is still moving, which is the length of the longest carry chain.

Integer width matters more than usual here. Java and Kotlin `int` and the TypeScript bitwise operators are 32-bit two's complement, so a carry out of bit 31 simply disappears, exactly as in hardware. Python integers are unbounded: a negative number behaves as if it had infinitely many 1 bits, so a carry never falls off and the loop would not end. The Python references therefore mask every intermediate value to 32 bits (`& 0xFFFFFFFF`) and convert a pattern with the sign bit set back into a negative number at the end.

## Approach: ripple-carry (Add bit by bit with a full adder)

### Intuition

Add the way a circuit does it: for each column from the lowest, combine the two input bits with the carry coming in. The sum bit is their XOR, and a carry goes out when at least two of the three are 1.

### Algorithm

1. Set `result = 0` and `carry = 0`.
2. For each bit position `p` from 0 to 31:
   1. Read `x = bit p of a` and `y = bit p of b`.
   2. Set bit `p` of `result` to `x ^ y ^ carry`.
   3. Set `carry = (x & y) | (carry & (x ^ y))`.
3. Return `result`, interpreted as a signed 32-bit value.

### Correctness

Column by column, this is the full-adder truth table: the three input bits add up to `2 * carry_out + sum_bit`, with `sum_bit = x ^ y ^ carry_in` (the parity) and `carry_out = 1` exactly when at least two inputs are 1. Long addition in base 2 is this rule applied from the lowest column up, so the 32 result bits are those of `a + b` modulo `2^32`. Because the true sum fits in 32 signed bits, reading those bits as two's complement gives exactly `a + b`.

### Complexity

- Time: O(32) — exactly 32 columns, each a constant number of bit operations: constant time.
- Space: O(1) — a few integers.

### Trade-offs

Transparent and close to hardware, so it is easy to verify, and its running time never depends on the values. It always does 32 rounds, while the other approach stops as soon as the carries are gone.

### Pitfalls and edge cases

- Read bits with an unsigned shift (`>>>`, `ushr`) or mask afterwards; with `>>` on a negative number, the copied sign bits do not matter here because only bit 0 is kept, but the habit avoids bugs elsewhere.
- In Python, mask the operands to 32 bits first, or bits beyond position 31 are never visited and negative inputs come out wrong.

### Language notes

- Python: after the loop, `result` is a 32-bit pattern; `~(result ^ 0xFFFFFFFF)` turns a pattern with the sign bit set into the negative number it represents.
- TypeScript: `(x ^ y ^ carry) << 31` produces a negative 32-bit number, which is the right sign; the result needs no conversion.
- Java and Kotlin: `int`/`Int` arithmetic is already 32-bit two's complement; Kotlin spells the operators `ushr`, `and`, `or`, `xor` and `shl`.

## Approach: xor-and-carry (Add without carries and repeat with the carries)

### Intuition

`a ^ b` adds every column at once but drops the carries. The carries are exactly the columns where both bits are 1, `a & b`, and each one belongs one column to the left: `(a & b) << 1`. So `a + b = (a ^ b) + ((a & b) << 1)`: a new addition of a "sum without carries" and the carries. Repeat until the carry part is 0.

### Algorithm

1. While `b` is not 0:
   1. `carry = (a & b) << 1`.
   2. `a = a ^ b`.
   3. `b = carry`.
2. Return `a` (in Python, after masking every step to 32 bits and converting the final pattern back to a signed value).

### Correctness

The identity `x + y = (x ^ y) + 2 * (x & y)` holds for all integers: per column, `x_i + y_i = (x_i ^ y_i) + 2 * (x_i & y_i)`. So the value `a + b` (modulo `2^32`) is unchanged by each round. The loop ends: after `k` rounds, the lowest `k` bits of `b` are 0, because a shifted-in carry always has a 0 in its lowest position and that zero region grows by at least one bit per round; with 32-bit words, `b` becomes 0 after at most 32 rounds. At that point `a` alone holds the sum.

### Complexity

- Time: O(32) — at most 32 rounds (the length of the longest carry chain plus one), usually only a handful for random operands.
- Space: O(1) — a few integers.

### Trade-offs

The standard interview answer: short, and fast because it handles all columns in parallel. The proof of termination relies on fixed-width words, which is exactly why Python needs the explicit mask.

### Pitfalls and edge cases

- Python without masking loops forever on mixed signs, for example `1 + (-1)`: the carry keeps moving left through infinitely many sign bits.
- Shift the carry, not the sum: `(a & b) << 1`, then XOR.
- Compute the carry before overwriting `a` with `a ^ b`.

### Language notes

- Python: `& 0xFFFFFFFF` after every shift keeps the carry inside 32 bits; the final `~(a ^ 0xFFFFFFFF)` restores a negative result.
- TypeScript: `&`, `^` and `<<` convert to 32-bit signed integers, so `(a & b) << 1` drops bit 31 exactly like Java's `int`; no masking is needed.
- Java: plain `int` arithmetic; `<< 1` discards the bit shifted out of position 31.
- Kotlin: the same with infix functions, `(sum and carry) shl 1` and `sum xor carry`; Kotlin parameters are read-only, so the reference copies them into `var`s.
