# Palindrome Partitioning: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| check-each-piece | intermediate | O(n^2 * 2^n) | O(n * 2^n) | the first correct version; no extra table |
| palindrome-table | optimal | O(n * 2^n) | O(n * 2^n) | default answer: every palindrome test becomes a table lookup |

A string of n equal letters has 2^(n-1) valid partitions (every one of the n - 1 gaps may or may not be cut), so exponential output is unavoidable. The approaches differ only in what each palindrome test costs.

## Approach: check-each-piece (Backtrack over cut positions and test each piece with two pointers)

### Intuition

Every partition starts with some palindromic prefix of `s`, and the rest of it is a partition of what remains. So try each prefix length, keep going whenever the prefix is a palindrome, and undo the choice before trying the next length.

### Algorithm

1. `cutFrom(start)` with a shared list `pieces`:
   1. If `start == n`, record a copy of `pieces` and return.
   2. For each `end` from `start` to `n - 1`: if `s[start..end]` is a palindrome (compare characters from both ends inward), append it, call `cutFrom(end + 1)`, and pop it.
2. Call `cutFrom(0)`.

### Correctness

By induction on the length of the suffix: `cutFrom(start)` records, after the current `pieces`, every palindrome partition of `s[start..]` exactly once. A partition of the suffix is a palindromic first piece `s[start..end]` followed by a partition of `s[end+1..]`; the loop tries every possible `end` once, keeps exactly the palindromic ones, and different `end` values give different first pieces, so no partition is produced twice. The empty suffix has exactly one partition, the empty one.

### Complexity

- Time: O(n^2 * 2^n) — there are at most 2^(n-1) partitions, so at most about 2^n recursion nodes; each node tries up to n end positions, and each two-pointer test costs up to n.
- Space: O(n * 2^n) — up to 2^(n-1) partitions whose pieces hold n characters in total; the recursion depth and `pieces` add O(n).

### Trade-offs

Needs no preparation and is easy to read, which makes it the oracle. The same substrings are tested again and again in different branches (in `aaaa`, the piece `aa` at position 2 is tested in every branch that reaches position 2), which is exactly what the table removes.

### Pitfalls and edge cases

- Copy `pieces` when recording a partition.
- The loop bound is inclusive of the last character: the piece may run to the end of the string.
- A single character is always a palindrome, so the recursion never gets stuck; there is always at least one partition.

### Language notes

- Python: `s[start : end + 1]` slices the piece; slicing copies, which is fine for strings this short.
- TypeScript: `s.slice(start, end + 1)` takes the piece; indexing a string returns one-character strings that compare with `!==`.
- Java: `substring(start, end + 1)` and `charAt` comparisons; `List<List<String>>` matches the signature.
- Kotlin: `s[left++] != s[right--]` compares `Char` values and advances both pointers in one line.
- Go: indexing a string gives a `byte`, so `s[left] != s[right]` compares bytes, which is exact for the lowercase ASCII letters here, and `s[start:end+1]` slices a piece without copying. The `isPalindrome` closure is a plain function value; only `cutFrom` needs the `var cutFrom func(...)` declaration first, because it calls itself. `slices.Clone(pieces)` snapshots a finished partition.
- Rust: `s.as_bytes()` gives the bytes to compare, and `s[start..=end].to_string()` slices out a piece, which is valid because the letters are single-byte ASCII (a byte range inside a multi-byte character would panic). The recursion shares one `pieces` buffer through `&mut Vec<String>`, and `pieces.clone()` snapshots a finished partition.

## Approach: palindrome-table (Precompute every palindromic substring, then backtrack)

### Intuition

Whether `s[i..j]` is a palindrome depends only on its outer characters and on the inside `s[i+1..j-1]`. Filling a table of those answers once, from shorter substrings to longer ones, turns every test inside the backtracking into a constant-time lookup.

### Algorithm

1. Build `palindrome[i][j]` for `i <= j`, iterating `i` from `n - 1` down to 0 and `j` from `i` up: it is true when `s[i] == s[j]` and either `j - i < 2` or `palindrome[i + 1][j - 1]`.
2. Run the same backtracking as before, but test pieces with `palindrome[start][end]`.

### Correctness

The table rule is the definition of a palindrome read from the outside in: the outer characters match and the inside is a palindrome, where substrings of length 1 or 2 have an empty or single-character inside. Iterating `i` downwards guarantees that row `i + 1` is complete before row `i` reads it. With the table correct, the backtracking is the one above, whose correctness was shown there.

### Complexity

- Time: O(n * 2^n) — the table costs O(n^2), and the backtracking now does O(n) work per node (one O(1) lookup per end position, plus copying pieces at the leaves) over about 2^n nodes.
- Space: O(n * 2^n) — the output dominates; the table adds O(n^2) and the recursion O(n).

### Trade-offs

Removes the repeated two-pointer scans for an O(n^2) table, a good trade whenever partitions are numerous. The table is the same one the Palindromic Substrings and Minimum Palindrome Cuts problems use, so it is worth knowing; for the minimum-cuts variant, a second one-dimensional table replaces the backtracking entirely and runs in O(n^2).

### Pitfalls and edge cases

- Fill rows from the bottom up (or by increasing length); a top-down row order reads cells that are not computed yet.
- The `j - i < 2` guard must come before `palindrome[i + 1][j - 1]`: for `j == i` that cell would be below the diagonal.

### Language notes

- Python: `[[False] * n for _ in range(n)]` builds independent rows; `[[False] * n] * n` would share one row.
- TypeScript: `Array.from({ length: n }, () => new Array<boolean>(n).fill(false))` builds independent rows for the same reason.
- Java: `new boolean[n][n]` is initialized to `false`.
- Kotlin: `Array(n) { BooleanArray(n) }` creates one fresh row per index; `downTo` iterates `i` from the end.
- Go: `make([][]bool, n)` creates only the outer slice, so each row needs its own `make([]bool, n)`; a loop `for i := n - 1; i >= 0; i--` walks the rows from the end. The `&&` and `||` short-circuit, so `palindrome[i+1][j-1]` is read only when `j-i >= 2`.
- Rust: `vec![vec![false; n]; n]` clones the inner vector once per row, so the rows are independent; `(0..n).rev()` walks `i` from the end. The `&&` and `||` short-circuit, so `j - 1` and `i + 1` are computed only when `j - i >= 2`, and the `usize` subtraction cannot underflow.
