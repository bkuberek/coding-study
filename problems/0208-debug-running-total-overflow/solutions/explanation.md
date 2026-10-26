# Debug: Running Total Overflow: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| long-accumulator | optimal | O(n) | O(1) | default answer: compute in `long` from the first multiplication on |

## Approach: long-accumulator (Widen before multiplying)

### Intuition

The arithmetic runs in 32-bit `int`, and only the finished, already wrong result is widened to `long`. Java and Kotlin `int` arithmetic wraps silently modulo 2^32: `2147483647 + 1` is `-2147483648`, with no exception and no warning. Two separate operations overflow:

1. **The running sum.** `total` is an `int` (in Kotlin, `sumOf` with an `Int` selector returns `Int`). Once the sum passes 2^31 - 1 it wraps negative. That is the `-$21,474,836.48` invoice: exactly 2^31 cents wrapped to -2^31.
2. **Each product.** `unitPrices[i] * quantities[i]` multiplies two `int`s, so the product is an `int` too, before it ever meets the accumulator. 10^6 * 10^5 = 10^11 wraps to 1,215,752,192, a positive and plausible-looking number. That is the `$12,157,521.92` invoice.

`(long) total` and `.toLong()` widen a value whose high bits are already gone. The fix is a wider type *during* the computation: a `long` accumulator, and at least one operand widened to `long` before the multiplication.

### Debugging approach

1. **Reproduce at the boundary.** Small invoices pass, so search for the threshold. A total of 2,147,483,647 cents (test `h4`) is right; one more cent (`h5`) comes out as -2,147,483,648. A sharp threshold at a power of two is the fingerprint of integer overflow.
2. **Check the numbers in the ticket.** -21,474,836.48 dollars is -2^31 cents. 12,157,521.92 dollars is 10^11 mod 2^32 cents. The five-cent invoice is 2^32 + 5 cents. Each one is the true value wrapped modulo 2^32.
3. **Find every 32-bit operation.** Read the expression types, not the variable you return: `total` is `int`, `unitPrices[i] * quantities[i]` is `int * int`. In Kotlin, hover over `sumOf` in the IDE: the selector returns `Int`, so the `Int` overload is chosen.
4. **Test each half-fix against the ticket.** A `long` accumulator alone fixes `h5`, `h7` and `h9` but still fails `h6`, `h8` and `h11`, where one line exceeds 2^31 - 1. Widening the product but keeping an `int` total fixes nothing that overflows. Only both together pass.

### Algorithm

1. Start a `long` total at `0`.
2. For each line `i`, widen `unitPrices[i]` to `long`, multiply by `quantities[i]` (which is promoted to `long`), and add the product to the total.
3. Return the total.

### Correctness

Every operand is at most 10^6, so each product is at most 10^12 and, over at most 1000 lines, the total is at most 10^15. Both fit easily in a 64-bit `long` (maximum about 9.2 * 10^18). Casting one operand before the multiplication makes Java and Kotlin compute the product in 64 bits. Each addition is also 64-bit, and no intermediate value comes near the limit, so every operation is exact and the returned total equals the mathematical sum.

### Complexity

- Time: O(n) — one multiplication and one addition per line.
- Space: O(1) — one accumulator.

### Trade-offs

`long` is the right fix at these sizes: it is exact, fast and needs no allocation. `Math.multiplyExact` and `Math.addExact` (Java, also callable from Kotlin) add overflow detection: they throw `ArithmeticException` instead of wrapping. They are worth it at system boundaries where limits are not guaranteed. `BigInteger` or `BigDecimal` never overflow but allocate per operation and make the code noisier. Use them when amounts are unbounded or need decimal scale and rounding rules. A `double` is wrong for money: it cannot represent most cent values exactly and loses whole cents above 2^53.

### Pitfalls and edge cases

- The general trap: the type of an expression is decided by its operands, not by the variable or return type that receives it. `long x = a * b;` with `int a, b` overflows before the assignment.
- `(long) (a * b)` casts too late. `(long) a * b` casts first, because a cast binds tighter than `*`.
- In Java, `int total; total += (long) a * b;` compiles: compound assignment hides a narrowing cast back to `int`. The overflow comes back without any warning.
- In Kotlin, `sumOf { a * b }` picks its overload from the lambda's type. An `Int` lambda gives an `Int` sum, which then overflows quietly.
- Wrapped values are not always negative. 10^11 wraps to a positive 1,215,752,192, and 2^32 + 5 wraps to 5. "Check for negative totals" does not detect overflow.

### Prevention

- Pick the accumulator type from the largest possible value, computed from the constraints (here 10^15), and write that bound down next to the code.
- Test at the boundary: totals of 2^31 - 1 and 2^31, and one line whose product alone exceeds 2^31 - 1.
- Use exact arithmetic (`Math.addExact`, `Math.multiplyExact`) where inputs are not bounded by contract.
- Static analysis catches the common forms. Error Prone's `IntLongMath` and SpotBugs' `ICAST_INTEGER_MULTIPLY_CAST_TO_LONG` flag an `int` multiplication that is later widened to `long`.
- Model money as a value type, for example a `Money` class wrapping a `long` of cents, so that arithmetic happens in one place, with one set of overflow rules.

### Language notes

- Java: `int` and `long` overflow wraps silently in two's complement. `Math.toIntExact`, `addExact` and `multiplyExact` throw instead. Compound assignment operators (`+=`, `*=`) include an implicit narrowing cast.
- Kotlin: `Int` arithmetic also wraps silently; there is no checked mode. Unlike Java, Kotlin never widens implicitly: `val total: Long = a * b` with `Int` operands does not compile, so the overflow hides in a call such as `sumOf` or `.toLong()`. `a.toLong() * b` widens first; `Long * Int` has an overload returning `Long`.
- Python and TypeScript are not listed. Python integers are arbitrary-precision. TypeScript numbers are doubles, exact up to 2^53, so the same code is exact at these sizes, although `Math.imul` and the bitwise operators (`| 0`) bring 32-bit wrapping back.
