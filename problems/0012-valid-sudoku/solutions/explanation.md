# Valid Sudoku: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(N^3) | O(1) | as a correctness oracle; no extra memory at all |
| hash-sets | optimal | O(N^2) | O(N^2) | default answer; clearest one-pass solution |
| bitmask | optimal | O(N^2) | O(N) | when memory or constant factors matter |

The board is always 9 x 9, so every approach runs in constant time on this problem, and the test ladder cannot tell them apart by board size. What the ladder varies is the number of filled cells n: every approach skips an empty cell and checks a filled one against its row, column and box, so on the fixed board each one grows linearly with n. The complexities above use the side length N (here N = 9, with sqrt(N) x sqrt(N) boxes) to show how each approach would scale on a larger board, which is the usual interview follow-up.

## Approach: brute-force (Scan the row, column and box of every filled cell)

### Intuition

A board breaks the rules exactly when some filled cell shares its digit with another cell of its row, its column or its box. Check that directly for every filled cell.

### Algorithm

1. For each cell holding a digit `d`:
   1. Scan the other cells of its row; if one holds `d`, return `false`.
   2. Scan the other cells of its column; if one holds `d`, return `false`.
   3. Scan the other cells of its box; if one holds `d`, return `false`.
2. Return `true`.

The references fuse the three scans into one loop over `i` from 0 to 8, reading row cell `i`, column cell `i` and box cell `i` together.

### Correctness

If two cells of one unit hold the same digit, the scan from either of them reaches the other and returns `false`. If every scan finishes, no filled cell shares its digit with another cell of any of its three units, which is exactly the rule. Each scan skips the cell itself, so a digit never conflicts with its own position.

### Complexity

- Time: O(N^3) — each of the N^2 cells scans about 3N cells. On a 9 x 9 board that is at most 81 * 27 = 2,187 comparisons.
- Space: O(1) — a few indices.

### Trade-offs

It needs no memory and is easy to verify, which makes it a good oracle. It compares each conflicting pair twice and rescans every unit once per filled cell; on a 9 x 9 board this is irrelevant, but on an N x N board the extra factor of N shows up.

### Pitfalls and edge cases

- The box scan must skip the cell itself, which is not enough to check by row or column alone: test both coordinates.
- The top-left corner of the box is `row - row % 3`, `column - column % 3`; the `i`-th cell of the box is at offset `(i / 3, i % 3)` from there.
- Empty cells (`.`) must be skipped, or every `.` conflicts with the next one.

### Language notes

- Python: cells are one-character strings, so compare with `"."` and with the digit string.
- TypeScript: `char[][]` arrives as `string[][]` of one-character strings; integer division needs `Math.floor`.
- Java: `char[][]` cells compare with `==` as primitives.
- Kotlin: `Array<CharArray>`; `Char` comparisons with `==` and `!=` work on values.

## Approach: hash-sets (One pass with a set per row, column and box)

### Intuition

Each rule is a duplicate check within a group of cells, and a set detects duplicates: before adding a digit, test whether it is already in the set. With 9 sets for rows, 9 for columns and 9 for boxes, one pass over the board checks every rule.

### Algorithm

1. Create 9 empty sets each for rows, columns and boxes.
2. For each cell `(r, c)` holding a digit `d`:
   1. Compute its box index `b = (r / 3) * 3 + c / 3`.
   2. If `d` is already in `rows[r]`, `columns[c]` or `boxes[b]`, return `false`.
   3. Add `d` to all three sets.
3. Return `true`.

### Correctness

The box index formula maps the nine cells of each 3 x 3 box to the same number from 0 to 8 and different boxes to different numbers. Invariant: before visiting a cell, each set holds exactly the digits of the already visited cells of its unit. A duplicate within a unit is therefore detected when its second occurrence is visited, and if no lookup succeeds, every unit holds distinct digits.

### Complexity

- Time: O(N^2) — every cell is visited once, with O(1) average set operations.
- Space: O(N^2) — 3N sets, each holding up to N digits.

### Trade-offs

The standard interview answer: one pass, easy to explain, and it generalizes to any board size. It allocates 27 hash sets for 81 cells, so its constant factor is higher than the bit masks. A common variant uses a single set of strings such as `"5 in row 3"`, `"5 in column 4"` and `"5 in box 1"`, which is shorter but slower because it builds strings.

### Pitfalls and edge cases

- Getting the box index wrong (for example `r / 3 + c / 3`) merges different boxes and reports false conflicts.
- In Java, `List<Set<Character>>` boxes every `char`; `Set.add` returning `false` doubles as the "already seen" check.

### Language notes

- Python: `[set() for _ in range(9)]` creates nine independent sets; `[set()] * 9` would share one.
- TypeScript: `Array.from({ length: 9 }, () => new Set<string>())` for the same reason; `Math.floor` for the box index.
- Java: lists of `HashSet<Character>`; the three `add` calls short-circuit, which is fine because any failure returns `false` immediately.
- Kotlin: `List(9) { HashSet<Char>() }` calls the initializer once per set.

## Approach: bitmask (One pass with a bit mask per row, column and box)

### Intuition

A set of digits from 1 to 9 fits in the low 9 bits of an integer: bit `d - 1` is set when digit `d` has been seen. Testing and adding become a bitwise AND and OR, so 27 integers replace 27 sets.

### Algorithm

1. Create 9 zero masks each for rows, columns and boxes.
2. For each cell `(r, c)` holding a digit `d`:
   1. Let `bit = 1 << (d - 1)` and `b = (r / 3) * 3 + c / 3`.
   2. If `(rows[r] | columns[c] | boxes[b]) & bit` is non-zero, return `false`.
   3. Set the bit in all three masks with OR.
3. Return `true`.

### Correctness

Each mask encodes the same set as the corresponding hash set of the previous approach: bit `d - 1` is set exactly when digit `d` was added. OR-ing the three masks and testing one bit is equivalent to testing membership in any of the three sets. The argument of the previous approach then carries over unchanged.

### Complexity

- Time: O(N^2) — one visit per cell with O(1) bit operations.
- Space: O(N) — 3N integers; for N up to 64, each mask fits in one machine word.

### Trade-offs

Fastest and smallest, with no allocation beyond three small arrays. Slightly less readable than sets, and it only works while N fits in the integer width (N up to 32 for `int`, 64 for `long`). Interviewers like it as a follow-up to the hash-set solution.

### Pitfalls and edge cases

- Shift by `d - 1`, not by the character code: the cell holds the character `'5'`, not the number 5.
- Test `(mask & bit) != 0`, not `== 1`: the bit is usually not the lowest one.

### Language notes

- Python: `int(digit)` converts the character; Python integers are unbounded, so `1 << 8` is trivially safe.
- TypeScript: `Number(cell)` converts the character; bitwise operators work on 32-bit integers, and an `Int32Array` keeps the masks unboxed.
- Java: `cell - '1'` turns the character into a shift distance directly; parenthesize `(a & bit) != 0`, because `!=` binds tighter than `&` in Java.
- Kotlin: bit operations are the infix functions `shl`, `or` and `and`; infix calls bind tighter than `!=`, but the reference parenthesizes the test for clarity.
