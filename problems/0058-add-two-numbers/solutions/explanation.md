# Add Two Numbers: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| big-integer | brute | O((m + n)^2) | O(m + n) | a quick check with a big-number library; never the interview answer |
| digit-carry | optimal | O(max(m, n)) | O(max(m, n)) | default answer |

`m` and `n` are the digit counts of the two numbers. Every approach must read every digit and write `max(m, n)` or `max(m, n) + 1` digits, so O(max(m, n)) is the floor for both time and the output.

## Approach: big-integer (Convert to arbitrary-precision integers, add, convert back)

### Intuition

The lists are just numbers in disguise. Turn each into an arbitrary-precision integer, let the language add them, and turn the sum back into a list of digits.

### Algorithm

1. Read each list's digits and build the integer from its most significant digit down (`value = value * 10 + digit`), or from a reversed decimal string.
2. Add the two integers.
3. Emit the sum's digits from least to most significant (repeated `divmod` by 10, or the decimal string read backwards) as new nodes.

### Correctness

Step 1 evaluates `d0 + 10 d1 + 100 d2 + ...`, the value the list represents. Arbitrary-precision addition is exact, and step 3 is the inverse of step 1, writing the digits of the sum least significant first, with no leading zeros because the most significant digit of a positive integer's decimal form is nonzero (and 0 is written as the single digit 0).

### Complexity

- Time: O((m + n)^2) — the addition itself is linear, but converting between decimal digits and a binary big integer with schoolbook arithmetic multiplies or divides a growing number by 10 once per digit, which is quadratic in the digit count. Library conversions can be faster: Java's `BigInteger(String)` is quadratic with a small constant and its `toString` divides and conquers on large values, and current V8 parses and prints a `bigint` in nearly linear time, so the TypeScript reference converts one digit at a time like the Python one.
- Space: O(m + n) — the big integers, the strings and the output list.

### Trade-offs

Short, and correct in every language that has big integers, which makes it a good oracle. It sidesteps the point of the problem (digit-wise carry handling) and is asymptotically slower. A 64-bit version would be wrong: test `h8` has 21 digits, beyond `Long.MAX_VALUE`.

### Pitfalls and edge cases

- Using `long` or `double` overflows or loses precision past about 18 or 15 digits.
- Python limits `int(str)` and `str(int)` to 4300 digits by default (`sys.set_int_max_str_digits`), so the reference builds the integer arithmetically and emits digits with `divmod`.
- The sum 0 must still produce one node; the `while True` loop in Python and the `do ... while` loop in TypeScript emit the digit before testing for zero.

### Language notes

- Python: integers are arbitrary precision; `divmod(total, 10)` returns the quotient and the last digit in one call.
- TypeScript: `bigint` literals such as `10n` keep the arithmetic exact; `BigInt(digit)` converts a number, `/` on two `bigint`s truncates and `Number(total % 10n)` takes the last digit back out.
- Java: `java.math.BigInteger` parses with `new BigInteger(String)` and adds with `add`; `StringBuilder.reverse()` puts the most significant digit first.
- Kotlin: `String.toBigInteger()` and the `+` operator on `BigInteger` come from the standard library's extensions; `Char.digitToInt()` converts a digit character.

## Approach: digit-carry (Grade-school addition with a carry)

### Intuition

The lists already store the digits in the order you add them on paper: ones first, then tens, and so on. Walk both lists in step, add the two digits and the carry, write down the last digit of that sum, and carry the rest.

### Algorithm

1. Create a dummy node; set `tail = dummy` and `carry = 0`.
2. While `l1` or `l2` has a node left, or `carry` is nonzero:
   1. `total = carry + (l1's digit or 0) + (l2's digit or 0)`; advance the lists that had a digit.
   2. Append a node with `total % 10` and set `carry = total / 10` (integer division).
3. Return `dummy.next`.

### Correctness

Invariant: after processing the first `i` digit positions, the nodes after the dummy are the lowest `i` digits of the sum, and `carry` (0 or 1) is what those positions overflow into position `i`. Each step adds the two digits of position `i` plus that carry, at most 9 + 9 + 1 = 19, so the new digit is `total % 10` and the new carry `total / 10` is again 0 or 1. The loop runs until no digits and no carry remain, so the most significant digit of the sum is emitted, and it is never a leading zero: the last step either reads a nonzero most significant input digit or emits a carry of 1.

### Complexity

- Time: O(max(m, n)) — one iteration per digit position, plus at most one for the final carry.
- Space: O(max(m, n)) — the output list; the extra memory beyond the output is O(1).

### Trade-offs

Linear, needs no big-number library, and works for numbers of any length; this is the expected answer. The same carry loop is the core of the follow-ups (most significant digit first, where you reverse the inputs or use stacks, and subtraction with borrows).

### Pitfalls and edge cases

- Stopping when both lists end loses a final carry: 999 + 1 needs a fourth node.
- Advancing only while both lists have nodes drops the tail of the longer number.
- In the shorter list's absence, add 0, not the last digit seen.

### Language notes

- Python: `divmod(total, 10)` gives the carry and the digit at once.
- TypeScript: `/` is floating-point division, so the carry needs `Math.floor(total / 10)`; `total % 10` is exact for small non-negative integers.
- Java: integer `/` and `%` give the carry and digit; the parameters are reassigned as cursors, which is idiomatic for Java list walks.
- Kotlin: ``first?.`val` ?: 0`` reads a digit or 0 in one expression, and `first?.next` advances only a non-null cursor.
