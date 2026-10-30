# Interleaving String: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; stops early on easy inputs; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard answer; the table also gives the split |
| rolling-array | optimal | O(m * n) | O(min(m, n)) | default answer when only true or false is needed |

Here m and n are the lengths of `s1` and `s2`. The state is how many characters of each source are used; the matched part of `s3` is then determined (its first `i + j` characters). Backtracking without a memo, trying "take from `s1`" and then "take from `s2`" whenever both match, is correct but exponential: with `s1 = s2 = "aaa...a"` and an `s3` that fails only at its last character, it tries every one of the C(m + n, m) ways to split the a's. It is described but not among the references.

The time classes use the total length of `s1` and `s2` as n.

## Approach: memoization (Recursion over how much of each string is used with a memo table)

### Intuition

The next character of `s3` must come from the front of `s1` or the front of `s2`. Try both when both match. The future only depends on the pair `(i, j)` of characters used so far, not on the order in which they were taken, so the result for each pair can be cached; a pair that failed once fails every time it is reached again.

### Algorithm

1. If `len(s1) + len(s2) != len(s3)`, return false.
2. Let `solve(i, j)` say whether `s1[i:]` and `s2[j:]` interleave to `s3[i + j:]`; `solve(m, n)` is true.
3. `solve(i, j)` is true if `s1[i] == s3[i + j]` and `solve(i + 1, j)`, or if `s2[j] == s3[i + j]` and `solve(i, j + 1)`.
4. Cache each result; return `solve(0, 0)`.

### Correctness

An interleaving of the suffixes starts with the first character of one of them, and that character must equal `s3[i + j]`; removing it leaves an interleaving of the remaining suffixes. Conversely, prefixing such an interleaving with the matching character gives one for the larger pair. So the recurrence is exact. With equal lengths, `(m, n)` matches the whole of `s3`, which is the base case; each call increases `i + j`, so the recursion terminates.

### Complexity

- Time: O(m * n) — at most (m + 1)(n + 1) states, each decided once from two cached answers; a true answer can stop much earlier.
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m + n.

### Trade-offs

Natural to write and often fast in practice, because it only visits reachable pairs and stops at the first full interleaving; it is the oracle. Its worst case equals the table's, with the overhead of recursion and up to 2,000 levels of stack at the limits.

### Pitfalls and edge cases

- Check the lengths first; otherwise an `s3` with extra characters can look valid.
- Greedy choice of source is wrong when both fronts match (`"aab"`, `"abb"`, `"aababb"`): the cache, not a heuristic, removes the repeated work.
- Empty strings: `("", "", "")` is true, and an empty `s1` reduces to `s2 == s3`.

### Language notes

- Python: `None` marks unknown entries in a list-of-lists cache.
- TypeScript: an `Int8Array` per row with -1, 0 and 1; `||` short-circuits so the second source is tried only when the first fails.
- Java: a `Boolean[][]` uses `null` for unknown and unboxes on return; a `byte[][]` with three values avoids the boxing.
- Kotlin: `arrayOfNulls<Boolean>` and the `?: run { ... }` idiom compute and store a missing entry.
- Go: a small `verdict` type (`unknown`, `yes`, `no`) in an `int8` table. Its zero value is `unknown`, so `make` already marks every cell unknown. `&&` and `||` short-circuit, so `s3[i+j]` is read only while a source still has a character.
- Rust: `Option<bool>` is the three-valued cell, and `&&` and `||` short-circuit as in the other languages, so the second source is tried only when the first fails.

## Approach: tabulation (Table of reachable prefix pairs)

### Intuition

Build the answer forwards: `reach[i][j]` says whether `s1[:i]` and `s2[:j]` interleave to `s3[:i + j]`. The last character of that prefix of `s3` came from `s1` (then `reach[i - 1][j]` must hold) or from `s2` (then `reach[i][j - 1]` must hold).

### Algorithm

1. If the lengths do not add up, return false.
2. Set `reach[0][0] = true`.
3. For every `i` from 0 to `m` and `j` from 0 to `n` (except `(0, 0)`): `reach[i][j]` is true if `i > 0`, `reach[i - 1][j]` and `s1[i - 1] == s3[i + j - 1]`, or if `j > 0`, `reach[i][j - 1]` and `s2[j - 1] == s3[i + j - 1]`.
4. Return `reach[m][n]`.

### Correctness

The recurrence is the memoized one, read from the end of the prefixes instead of the front of the suffixes. Row-major order computes `reach[i - 1][j]` and `reach[i][j - 1]` before `reach[i][j]`; row 0 and column 0 handle "only one source used so far".

### Complexity

- Time: O(m * n) — two constant-time checks per cell.
- Space: O(m * n) — the full table.

### Trade-offs

No recursion and a fixed amount of work; the table can be walked back from `(m, n)` to recover which source each character came from. It always fills every cell, even when the answer is decided early.

### Pitfalls and edge cases

- The index into `s3` is `i + j - 1`, not `i - 1` or `j - 1`.
- Cells with `i = 0` or `j = 0` need their own guards, because one neighbor does not exist.

### Language notes

- Python and TypeScript: nested boolean arrays; Java `boolean[][]` and Kotlin `BooleanArray` rows start out false.
- Go and Rust: `make([]bool, columns+1)` per row and `vec![vec![false; columns + 1]; rows + 1]` start out false. In Rust the `i > 0` and `j > 0` tests come first in each `&&` chain, so `i - 1`, `j - 1` and `i + j - 1` never run on a zero `usize`.

## Approach: rolling-array (One row of reachable prefixes along the shorter string)

### Intuition

Row `i` of the table reads only row `i - 1` (the cell just above) and the cell to its left in row `i`. A single array can hold both: before `reach[j]` is overwritten it still holds the value from the row above, and `reach[j - 1]` already holds the current row. Swapping `s1` and `s2` does not change the answer, so the row can run along the shorter source.

### Algorithm

1. Check the lengths; let `shorter` be the shorter source.
2. For each row `i` from 0 to `len(longer)` and each `j` from 0 to `len(shorter)`: set `reach[j]` to `(reach[j] and longer[i - 1] == s3[i + j - 1])` or `(reach[j - 1] and shorter[j - 1] == s3[i + j - 1])`, with `reach[0]` true for `(0, 0)`.
3. Return `reach[len(shorter)]`.

### Correctness

Invariant: after row `i`, `reach[j]` equals the full table's `reach[i][j]`. The in-place update reads the old `reach[j]` (row `i - 1`) and the new `reach[j - 1]` (row `i`), exactly the two neighbors of the recurrence. Exchanging the roles of the two sources maps interleavings to interleavings, so choosing the shorter one for the row is safe.

### Complexity

- Time: O(m * n) — the same cells as the table.
- Space: O(min(m, n)) — one row.

### Trade-offs

The usual follow-up answer: same speed, far less memory. Like the full table it does all the work even when the answer is decided early, and it cannot recover the split.

### Pitfalls and edge cases

- Overwrite `reach[j]` in every cell, including with false: a stale true from the row above would leak into the current row.
- Row 0 has no "from longer" option; `i > 0` guards it.

### Language notes

- The four references are the same loop; Kotlin and Java use `BooleanArray` and `boolean[]`, Python and TypeScript plain arrays.
- Go and Rust are the same loop over a `[]bool` or `Vec<bool>`. As in the table version, Rust puts `i > 0` and `j > 0` before every subtraction, so a `usize` never underflows; the cell `(0, 0)` is set once and the loop moves on.
