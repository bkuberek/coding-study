# Lamp Patterns: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| filter-all-strings | brute | O(n * 2^n) | O(n * 1.62^n) | as a cross-check, or to see how much work pruning saves |
| choose-explore-undo | optimal | O(n * 1.62^n) | O(n * 1.62^n) | default answer: every string it finishes is already valid |

The number of allowed patterns is the Fibonacci number F(n + 2), which grows by a factor of about 1.618 per extra lamp, so the output alone is about n * 1.62^n characters. The brute force looks at all 2^n strings, and the ratio of 2^n to the answer count grows by about 1.24 per lamp.

## Approach: filter-all-strings (Write all 2^n strings of 0 and 1, keep those without two 1s in a row)

### Intuition

Every arrangement of `n` lamps is a string of `n` characters from `0` and `1`, so there are exactly 2^n of them. Write them all and throw away the ones that break the rule. Counting from 0 to 2^n - 1 in binary, padded with zeros on the left to `n` digits, writes every string once and already in increasing order.

### Algorithm

1. For each number from 0 to 2^n - 1:
   1. Write it in binary, padded on the left with `0` to length `n`.
   2. Keep the string if it does not contain `"11"`.
2. Return the kept strings in the order they were written.

### Correctness

Binary numerals of a fixed length are in one-to-one correspondence with the numbers they stand for, so the loop writes each of the 2^n strings exactly once, and a larger number gives a string that is larger in dictionary order. A string is allowed exactly when no two neighbouring characters are both `1`, which is what the `"11"` search tests.

### Complexity

- Time: O(n * 2^n) — each of the 2^n strings is written and searched in O(n).
- Space: O(n * 1.62^n) — the kept strings, F(n + 2) of them with n characters each; the loop itself holds one string at a time.

### Trade-offs

It is the shortest correct program and a good cross-check for anything cleverer. It is also wasteful: at `n = 14` it writes 16,384 strings to keep 987. Backtracking removes that waste without changing what is produced.

### Pitfalls and edge cases

- Forgetting to pad with zeros: `5` is `"101"` for `n = 3` but `"0101"` for `n = 4`, and a missing leading `0` breaks both the length and the order.
- The test can also be done on the number itself: `number & (number >> 1)` is zero exactly when no two neighbouring bits are both set. That is a nice follow-up, but the string test is easier to read.

### Language notes

- Python: `format(number, f"0{n}b")` writes the padded binary numeral in one step.
- TypeScript: `number.toString(2).padStart(n, "0")`; `2 ** n` is exact for the sizes here.
- Java: `Integer.toBinaryString` does not pad, so `"0".repeat(n - bits.length())` adds the zeros.
- Kotlin: `number.toString(2).padStart(n, '0')`, and `"11" !in pattern` reads as a membership test.
- Go: the reference fills one reused `[]byte` with the bits of `number`, most significant first, and calls `strings.Contains` on its string form; `'0' + byte(bit)` turns a bit into its character.
- Rust: `format!("{:0width$b}", number, width = n as usize)` pads with zeros; the shift `1_u32 << n` needs `n` small enough, which the constraint guarantees.

## Approach: choose-explore-undo (Choose a lamp state, explore the rest, undo the choice; never choose 1 after 1)

### Intuition

This is backtracking: build the answer one position at a time, and at every position follow the same three steps. Choose a value for the next lamp, explore everything that can follow, then undo the choice so the next value can be tried from the same starting point. The only extra idea is pruning: a lamp may be switched on only when the lamp to its left is off, so a branch that would create two `1`s in a row is never entered. Backtracking is a standard way to write such searches; Golomb and Baumert wrote it up as "Backtrack Programming" in 1965 (Journal of the ACM 12(4):516-524, doi 10.1145/321296.321300), and, as NIST's Dictionary of Algorithms and Data Structures records, they credit D. H. Lehmer with the name.

### Algorithm

1. Keep one shared list of characters, `lamps`, and a recursive function `extend()`.
2. If `lamps` already has `n` characters, copy it into the result and return.
3. Choose `0`: append it, call `extend()`, then remove it again.
4. If `lamps` is empty or its last character is `0`, choose `1` in the same way: append it, call `extend()`, then remove it.
5. Call `extend()` once from the empty list and return the result.

### Correctness

Invariant: when `extend()` is called, `lamps` is an allowed prefix, and after the call returns it is exactly as it was before. The two choices cover both possible values of the next lamp, and `1` is skipped only when the previous lamp is on, in which case every string beginning that way would contain `"11"`. So every allowed string is reached by exactly one path of choices, and no forbidden string is ever completed. Trying `0` before `1` at every position visits the strings in increasing order.

### Complexity

- Time: O(n * 1.62^n) — the recursion tree has F(n + 2) leaves and every internal node leads to at least one of them, so it has O(1.62^n) nodes; copying a finished string costs O(n).
- Space: O(n * 1.62^n) — the result; the shared list and the recursion need only O(n) beyond it.

### Trade-offs

Both approaches have the same shape of answer, but this one never builds a string it will discard, and its running time follows the number of answers instead of 2^n. It is also the template for the harder problems in the same family: the rule that prunes changes (balanced brackets, queens that do not attack each other, a target sum), while choose, explore and undo stay the same.

### Pitfalls and edge cases

- Forgetting the undo step leaves stale characters in the shared list, and every later string is wrong.
- Appending the shared list itself to the result stores a reference that later changes; copy it (`"".join`, `toString`, `string(...)`, `clone`) at the moment it is complete.
- The first lamp has no left neighbour, so the check must allow `1` when the list is empty.
- `n = 1` gives `["0", "1"]`: the pruning rule never fires.

### Language notes

- Python and TypeScript: a nested function closes over `result` and `lamps`; `"".join(lamps)` and `lamps.join("")` copy the characters into a new string.
- Java: a `StringBuilder` is the shared buffer; `deleteCharAt(length - 1)` is the undo, and `toString()` copies it.
- Kotlin: a local `fun` closes over the `StringBuilder`; `lamps.last()` reads the last character.
- Go: `lamps = lamps[:len(lamps)-1]` shortens the slice for the undo, and `string(lamps)` copies the bytes into a new string, which keeps later changes out of the result.
- Rust: the buffer and the result are passed down as `&mut` references; `String::pop` is the undo, `ends_with('1')` reads the previous lamp, and `clone()` copies the finished string.
