# Multiply Strings: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| add-partial-products | brute | O(n * (m + n)) | O(m + n) | you want to mirror long multiplication on paper |
| digit-grid | optimal | O(m * n) | O(m + n) | default answer |

`m` and `n` are the digit counts of `num1` and `num2`. Both approaches are quadratic, like schoolbook multiplication; the grid version avoids building and re-adding a full row for every digit, which roughly halves the work and removes most allocations. Space counts the working digits, which are as long as the result.

## Approach: add-partial-products (Add one shifted partial product per digit)

### Intuition

Do exactly what long multiplication on paper does: multiply `num1` by one digit of `num2` at a time, shift that row by the digit's position, and add the rows. Two small helpers suffice, "big number times one digit" and "big number plus big number", both on little-endian digit lists so that carries move towards the end.

### Algorithm

1. Return `"0"` if either factor is `"0"`.
2. Convert `num1` to little-endian digits.
3. For each digit `d` of `num2`, from the last one (shift 0) to the first:
   1. Compute `num1 * d` with one carry pass.
   2. Prepend `shift` zeros (multiply by `10^shift`).
   3. Add it to the running total with one carry pass.
4. Convert the total back to a string, most significant digit first.

### Correctness

`num1 * num2 = sum over positions s of num1 * d_s * 10^s`, where `d_s` is the digit of `num2` at position `s` from the right. Step 3 adds exactly these terms. The two helpers are the standard carry algorithms: each output digit is the value modulo 10 and the carry is the quotient, so every intermediate list is the exact decimal representation of its value. Both factors are non-zero after step 1, so the final total has no leading zeros: the leading digit of a carry pass is the last non-zero carry or digit.

### Complexity

- Time: O(n * (m + n)) — each of the `n` rows costs O(m) to build and O(m + n) to add.
- Space: O(m + n) — the running total and one row.

### Trade-offs

Close to how people multiply by hand, so it is easy to explain and to check. It allocates a new row and a new total for every digit of `num2` and re-adds the long tail of the total each time; the grid approach accumulates in place.

### Pitfalls and edge cases

- Handle `"0"` first, or the result has to be stripped of leading zeros (`"000"`).
- Keep the lists little-endian; adding numbers stored most-significant-first needs right-aligned indexes everywhere.
- The shift is one zero per position, prepended in little-endian order (appended in the written number).

### Language notes

- Go: indexing a `string` yields a `byte`, so `int(num1[i] - '0')` reads a digit without creating substrings. Digits are little-endian `[]int` slices and every `add` allocates its result, as in the Python reference; `append(make([]int, shift), row...)` puts the shift zeros in front. The result is built in a `[]byte` and converted with one `string(text)` call.
- Rust: `String::bytes()` walks the ASCII digits, and `ch - b'0'` is a `u8` that `u32::from` widens before any multiplication, so `digit * factor + carry` (at most 90) never overflows. `left.get(position).copied().unwrap_or(0)` reads a digit or zero past the shorter number, and `char::from(b'0' + digit as u8)` turns a digit back into a character.

## Approach: digit-grid (Accumulate every digit product at position i + j)

### Intuition

Index both factors from the left. Digit `i` of `num1` has place value `10^(m - 1 - i)` and digit `j` of `num2` has `10^(n - 1 - j)`, so their product lands at place value `10^(m + n - 2 - i - j)`, which is position `i + j + 1` in a result array of `m + n` digits counted from the left. Adding every digit product into its position, and pushing carries one position to the left, produces the product in a single array without building any rows.

### Algorithm

1. Return `"0"` if either factor is `"0"`.
2. Create `digits` with `m + n` zeros.
3. For `i` from `m - 1` down to 0:
   1. Set `carry = 0`.
   2. For `j` from `n - 1` down to 0: `value = digits[i + j + 1] + num1[i] * num2[j] + carry`; store `value mod 10` at `i + j + 1` and set `carry = value div 10`.
   3. Add `carry` to `digits[i]`.
4. Skip a leading zero (there is at most one) and join the digits.

### Correctness

Invariant: after processing row `i`, the array holds the decimal digits of `num1[i..] * num2` (the suffix of `num1` from `i` times `num2`), aligned so that the last digit is at position `m + n - 1`. Processing row `i - 1` adds `num1[i - 1] * num2` shifted one place further left, using the same carry rule as in a column addition, so the invariant holds after every row. Every stored digit stays in 0..9, `value` is at most `9 + 81 + 9 = 99`, and the final carry goes into `digits[i]`, which no earlier row has touched. After row 0 the array is `num1 * num2` in `m + n` digits. A product of an `m`-digit and an `n`-digit number has `m + n - 1` or `m + n` digits, so at most one leading zero exists.

### Complexity

- Time: O(m * n) — one multiply-add per pair of digits.
- Space: O(m + n) — the result array.

### Trade-offs

The standard interview answer: one allocation, one tight double loop and no string concatenation inside it. Asymptotically faster methods exist (Karatsuba at about `n^1.585`, FFT-based multiplication near `n log n`) and are what big-integer libraries use for huge inputs, but they are rarely expected in an interview.

### Pitfalls and edge cases

- Position `i + j + 1`, not `i + j`: the extra slot at index 0 holds the final carry.
- With the per-step carry, `value` never exceeds `9 + 81 + 9 = 99` and every stored digit stays in 0..9. Deferring the carries (storing raw sums and normalizing once at the end) also works, because raw sums stay below `81 * min(m, n) + 9`, far inside 32 bits; forgetting to normalize at all is the bug to avoid.
- Converting characters: subtract the code of `'0'`; `int(ch)` in Python, `ch - '0'` in Java and Kotlin, `charCodeAt(i) - 48` in TypeScript.

### Language notes

- Python: `divmod` returns quotient and remainder in one call; the grid can be built as a list of ints and joined with `"".join(map(str, ...))`.
- TypeScript: a `Uint8Array` holds digits compactly; `charCodeAt` reads digits without creating substrings.
- Java: `charAt(i) - '0'` yields an `int`; a `StringBuilder` sized `m + n` builds the result without reallocation.
- Kotlin: `num1[i] - '0'` subtracts two `Char`s into an `Int`, and `'0' + digit` adds an `Int` to a `Char`; `buildString` wraps a `StringBuilder`.
- Go: the digits are read straight from the strings (`int(num1[i]-'0')`), and `digits` is one `[]int` allocated once at `m + n` entries. The result is assembled in a `[]byte` with capacity for exactly the digits kept, then converted once.
- Rust: `first` and `second` are `Vec<u32>` of digits, and `(0..len).rev()` counts down without the `usize` underflow a `>= 0` test would cause. The accumulated `digits[i + j + 1] + first[i] * second[j] + carry` is at most 99, so `u32` is ample, and `collect()` into a `String` joins the characters.
