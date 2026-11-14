# N-Queens: Explanation

## Overview

S is the number of valid placements (0, 0, 2, 10, 4, 40, 92, 352, 724 for n = 2 to 10); every approach writes S boards of n^2 squares.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-board | brute | O(n^2 * n!) | O(n^2 * S) | first working version; the conflict test is plain geometry |
| attacked-lines | optimal | O(n * n!) | O(n^2 * S) | default interview answer: constant-time conflict tests |
| bitmask | optimal | O(n!) | O(n^2 * S) | fastest; only iterates over the free squares of each row |

All three place one queen per row, top to bottom, and backtrack on conflicts. A placement with one queen per row and one per column is a permutation of the columns, so the search tree has at most n! leaves; the approaches differ in what a conflict test costs and in how many candidate squares each node looks at.

## Approach: scan-board (Place queens row by row, scanning earlier rows for conflicts)

### Intuition

Two queens in different rows attack each other exactly when they share a column or when their column distance equals their row distance (a diagonal). Place a queen in each row in turn; before using a square, compare it with every queen already on the board.

### Algorithm

1. Keep `queenColumn`, the columns of the queens in the rows placed so far.
2. `place(row)`:
   1. If `row == n`, draw the board and record it.
   2. For each `col`: if no earlier queen shares the column or satisfies `|col - otherCol| == row - otherRow`, put the queen there and call `place(row + 1)`; afterwards take it back.
3. Call `place(0)`.

### Correctness

Every valid placement has exactly one queen per row, so it is a sequence of column choices, one per row, and the search tries every sequence in which each new queen is safe against the earlier ones. A valid placement passes every one of those tests, so it is reached; a recorded board passed a test between every pair of queens, so it is valid. Different branches differ in the column of some row, so no board is recorded twice.

### Complexity

- Time: O(n^2 * n!) — the safe partial placements have distinct columns, so there are at most about e * n! of them; each tries n columns, and each test scans up to n earlier rows.
- Space: O(n^2 * S) — S boards of n strings of length n; the recursion and `queenColumn` add O(n).

### Trade-offs

Clear and easy to check, which makes it the oracle. The repeated scans make it a factor of n slower than keeping the attacked lines in sets. An even more naive brute force tries all n! column permutations and checks each at the end; it never prunes a doomed prefix, so it is slower again.

### Pitfalls and edge cases

- Use the absolute column difference; a diagonal can lean either way.
- n = 2 and n = 3 have no placement: the answer is an empty list, not a list with an empty board.
- Draw the board only at a leaf, from the recorded columns.

### Language notes

- Python: `all(...)` over a generator stops at the first conflict.
- TypeScript: `every` stops at the first conflict; `".".repeat(col)` draws a row.
- Java: an `int[]` of columns indexed by row needs no undo, since a row's entry is overwritten before it is read again.
- Kotlin: `(0 until row).all { ... }` reads like the definition; `kotlin.math.abs` handles the diagonal distance.
- Go: the standard library has `math.Abs` only for floating point, so the reference writes a three-line integer `abs`. A `for` loop with an early `return false` is the `all(...)`. `strings.Repeat(".", col) + "Q" + strings.Repeat(".", size-col-1)` draws a row, and a `draw` helper turns the column list into the board.
- Rust: `abs_diff` on two `usize` columns gives the distance without a signed type (and without an underflow), and `Iterator::all` over `enumerate()` stops at the first conflict. `".".repeat(col)` and `format!` draw a row.

## Approach: attacked-lines (Track used columns and diagonals in sets)

### Intuition

Every square lies on one column, one diagonal running down-right and one running down-left. On a down-right diagonal, `row - col` is the same for every square; on a down-left one, `row + col` is. Keep the columns and both kinds of diagonals that already hold a queen; a square is safe exactly when none of its three lines is taken, which is three lookups instead of a scan.

### Algorithm

1. Keep three marker structures: used columns, used `row - col` values and used `row + col` values.
2. `place(row)`:
   1. If `row == n`, draw the board and record it.
   2. For each `col` whose three lines are all free: mark them, record the column, call `place(row + 1)`, and unmark them.
3. Call `place(0)`.

### Correctness

Two queens attack each other exactly when they share a column, a `row - col` value or a `row + col` value (rows are distinct by construction). The markers hold exactly the lines of the queens currently placed, because each placement marks its three lines and the matching undo clears them; no two queens can share a line, so clearing never removes another queen's mark. The test is therefore equivalent to the scan, and the rest of the argument is the same as before.

### Complexity

- Time: O(n * n!) — the same search tree, now with an O(1) test per candidate square and n candidates per node; drawing boards costs O(n^2) per solution, which is far below n! here.
- Space: O(n^2 * S) — the output dominates; the markers need O(n) entries (n columns and 2n - 1 diagonals of each kind).

### Trade-offs

The standard answer: simple bookkeeping and a constant-time test. Arrays of booleans indexed by `row - col + n - 1` and `row + col` are faster than hash sets and just as clear. It still loops over all n columns at each node, including those already attacked; the bitmask version skips them.

### Pitfalls and edge cases

- `row - col` is negative for squares right of the main diagonal; offset it by `n - 1` when indexing an array.
- There are 2n - 1 diagonals of each kind, not n.
- Unmark exactly the three lines that were marked.

### Language notes

- Python: sets accept negative `row - col` keys directly, so no offset is needed.
- TypeScript: boolean arrays with the `n - 1` offset; chained assignment marks all three lines in one statement.
- Java: the reference keeps the markers in fields reset at the start of each call, which keeps the recursive method's signature short.
- Kotlin: a local `mark(row, col, used)` function sets or clears the three lines, so the undo mirrors the do.
- Go: there is no set literal, and a `map[int]struct{}` would do, but boolean slices are simpler and faster here: `columns` has `n` entries and the two diagonal arrays have `2n - 1`, with `row - col` shifted by `n - 1` so it is never negative. A multiple assignment sets or clears all three flags in one statement.
- Rust: three `Vec<bool>` live in a small `Lines` struct so the recursion takes one parameter instead of three. `row - col` can be negative and the indexes are `usize`, so the diagonal index is computed as `row + n - 1 - col`, which never goes below zero because `col <= n - 1`.

## Approach: bitmask (Keep the attacked squares of the next row as bits)

### Intuition

Represent the columns, the down-right diagonals and the down-left diagonals that attack the current row as three n-bit masks. Their union is the set of attacked squares, so its complement lists the free ones, and `free & -free` extracts them one at a time. Moving to the next row shifts each diagonal attack one column over: left for one direction, right for the other.

### Algorithm

1. Let `full = 2^n - 1`.
2. `place(columns, diagonals, antiDiagonals)`:
   1. If `columns == full`, every row has a queen: draw the board and record it.
   2. Let `free = full & ~(columns | diagonals | antiDiagonals)`.
   3. While `free` is not 0: take its lowest bit `bit`, remove it from `free`, record its column, and call `place(columns | bit, ((diagonals | bit) << 1) & full, (antiDiagonals | bit) >> 1)`.
3. Call `place(0, 0, 0)`.

### Correctness

Invariant: in a call for row `r`, bit `c` of `columns` is set exactly when some placed queen is in column `c`, and bit `c` of `diagonals` (or `antiDiagonals`) is set exactly when a placed queen lies on the down-right (or down-left) diagonal through `(r, c)`. A queen at `(r - 1, c')` covers `(r, c' + 1)` down-right and `(r, c' - 1)` down-left, which is what the shifts compute, and masking with `full` drops attacks that leave the board. So `free` is exactly the set of safe squares in row `r`, the search tries each of them once, and the argument of the scanning version applies.

### Complexity

- Time: O(n!) — each node iterates only over its free squares, so the work is proportional to the number of tree edges, at most about e * n!; drawing the S boards adds O(n^2 * S), which is smaller.
- Space: O(n^2 * S) — the output; the recursion holds O(n) frames of three integers.

### Trade-offs

The fastest of the three by a wide constant factor, and the version to use for counting placements (drop the drawing and return counts). Bit tricks are harder to read and to debug under interview pressure, and the masks limit n to the word size, which is irrelevant here.

### Pitfalls and edge cases

- Mask the left shift with `full`, or bits beyond column n - 1 accumulate (harmless for correctness only because `free` is masked too, but wasteful).
- `free & -free` relies on two's complement; it is the lowest set bit.
- Convert a bit to its column index with a trailing-zero count, not with a logarithm on floating-point numbers.

### Language notes

- Python: integers are unbounded, so `~` yields a negative number; `full & ~(...)` brings it back into n bits. `bit.bit_length() - 1` is the column.
- TypeScript: bit operators work on 32-bit integers; `31 - Math.clz32(bit)` is the column of a single set bit.
- Java: `Integer.numberOfTrailingZeros(bit)` is the column.
- Kotlin: `and`, `or`, `xor`, `inv`, `shl` and `shr` are the infix bit operators; the same `Integer.numberOfTrailingZeros` gives the column.
- Go: `&^` is AND NOT, so `full &^ (columns | diagonals | antiDiagonals)` is Python's `full & ~(...)` in one operator, and `free & -free` isolates the lowest set bit because `int` is signed two's complement. `bits.TrailingZeros(uint(bit))` from `math/bits` gives the column. In Go `<<` and `&` have the same precedence and group left to right, so `(diagonals|bit)<<1&full` shifts first and masks second.
- Rust: the masks are `u32`, which cannot be negated with `-`, so the lowest set bit is `free & free.wrapping_neg()`; `!` is bitwise NOT, and `trailing_zeros()` gives the column. The three masks travel together as a `[u32; 3]` to keep the recursive function's parameter list short.
