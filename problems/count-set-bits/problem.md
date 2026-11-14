# Count Set Bits

## Statement

You get an unsigned 32-bit integer `n`. Return how many of its 32 binary digits are 1, a quantity also called its population count or Hamming weight.

The input is unsigned: values from `2^31` to `2^32 - 1`, whose highest bit is set, are large positive numbers here, not negative ones. Because Java, Kotlin and TypeScript have no unsigned 32-bit type, the value arrives as a 64-bit `long` (a `number` in TypeScript); only its lowest 32 bits can be set.

Reference: this is our own wording of LeetCode problem 191, [Number of 1 Bits](https://leetcode.com/problems/number-of-1-bits/).

## Input

- `n`: an integer between `0` and `2^32 - 1`

## Output

The number of 1 bits in the binary representation of `n`.

## Examples

### Example 1

<!-- case: ex1 -->

44 is `101100` in binary: three of its bits are 1.

### Example 2

<!-- case: ex2 -->

`2^32 - 1 = 4294967295` has all 32 bits set. Treated as a signed 32-bit value it would be -1, which is why the input type is wider than 32 bits.

## Constraints

- `0 <= n <= 2^32 - 1`

## Follow-ups

- Testing each of the 32 positions always costs 32 steps. Can the number of steps depend only on how many bits are set?
- If this function were called millions of times, how could a small lookup table speed it up?
- Most CPUs have a single instruction for this. Which library call reaches it in your language?

## Hints

### Hint 1

`n & 1` is the lowest bit, and shifting right by one moves the next bit into its place.

### Hint 2

What does `n - 1` look like in binary, compared with `n`? Look at the lowest set bit and everything below it.

### Hint 3

`n & (n - 1)` is `n` with its lowest set bit cleared. Count how many times you can do that before reaching 0.
