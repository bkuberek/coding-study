# Regular Expression Matching: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; stops early on easy inputs; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard bottom-up answer |
| rolling-array | optimal | O(m * n) | O(n) | default answer with minimal memory |

Here m is the length of `s` and n the length of `p`. The state is a pair of positions, one in the string and one in the pattern, and its value says whether the rest of the string matches the rest of the pattern. Plain backtracking, trying "skip the starred item" and "use it once more" at every star, is correct but exponential: `"aaa...a"` against `"a*a*a*...a*b"` tries every way to distribute the a's among the stars before failing. Production engines that backtrack (including Python's `re`) show exactly this blow-up. That version is described but not among the references; one of the hidden cases is built to time it out.

The time classes use the length of `s` as n; the generated patterns are about as long as `s`.

## Approach: memoization (Recursion over string and pattern positions with a memo table)

### Intuition

Look at the next pattern item. Without a star it must match the next letter (a `.` matches any letter), and both positions advance. With a star there are two choices: skip the item entirely (it matched zero letters), or, if it matches the next letter, consume that letter and stay on the same starred item, which may consume more. The outcome depends only on the two positions, so cache it.

### Algorithm

1. Let `solve(i, j)` say whether `s[i:]` matches `p[j:]`.
2. If the pattern is exhausted (`j == len(p)`), the answer is whether the string is exhausted too.
3. Let `first` be whether `s[i]` exists and equals `p[j]` or `p[j]` is `.`.
4. If `p[j + 1]` is `*`: return `solve(i, j + 2)` or (`first` and `solve(i + 1, j)`).
5. Otherwise return `first` and `solve(i + 1, j + 1)`.
6. Cache every result; return `solve(0, 0)`.

### Correctness

A match of `p[j:]` against `s[i:]` assigns each pattern item a block of the string. For an unstarred item, the block is exactly one letter that the item accepts, and the rest must match the rest. For a starred item, the block is zero letters (then the rest of the pattern after the star matches all of `s[i:]`) or at least one letter, the first of which the item accepts; removing that letter leaves a match of the same starred item, with one fewer repetition, against `s[i + 1:]`. These cases are exhaustive, so the recurrence is exact. Each call moves `j` forward or `i` forward, so the recursion terminates.

### Complexity

- Time: O(m * n) — at most (m + 1)(n + 1) states, each decided in O(1) from cached results.
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m + n.

### Trade-offs

The most natural formulation and the oracle here; it only visits reachable states and often stops early. It still recurses up to 2,000 levels at the limits.

### Pitfalls and edge cases

- A star applies to the item before it, so look one character ahead (`p[j + 1]`) before deciding how to treat `p[j]`.
- An empty string can still match: `"a*b*"` and `".*"` match `""`.
- The match must cover all of `s`: reaching the end of the pattern with letters left is a failure.

### Language notes

- Python: `None` marks unknown entries; `p[j] in (s[i], ".")` tests both cases at once.
- TypeScript: an `Int8Array` per row with -1, 0 and 1.
- Java: a `Boolean[][]` with `null` for unknown.
- Kotlin: `arrayOfNulls<Boolean>` with the `?: run { ... }` idiom.
- Go: a small `verdict` type (`unknown`, `yes`, `no`) in an `int8` table, so `make` already marks every cell unknown. `first && solve(...)` short-circuits, so `s[i]` is read only when `i < len(s)`.
- Rust: `Option<bool>` cells and byte literals (`b'.'`, `b'*'`) over `as_bytes()`; `&&` and `||` short-circuit as in the other languages.

## Approach: tabulation (Table of prefix matches)

### Intuition

Use prefixes: `matches[i][j]` says whether `s[:i]` matches `p[:j]`. If `p[j - 1]` is a plain item, it must match `s[i - 1]` and the shorter prefixes must match. If it is a star, the starred item `p[j - 2]` either matches nothing (`matches[i][j - 2]`) or matches `s[i - 1]` as its last repetition, in which case `s[:i - 1]` must still match `p[:j]` with the same star.

### Algorithm

1. Create an `(m + 1) * (n + 1)` table of false and set `matches[0][0]` to true.
2. For `i` from 0 and `j` from 1:
   1. If `p[j - 1] == '*'`: `matches[i][j] = matches[i][j - 2]` or (`i > 0`, `p[j - 2]` matches `s[i - 1]`, and `matches[i - 1][j]`).
   2. Otherwise: `matches[i][j] = i > 0`, `p[j - 1]` matches `s[i - 1]`, and `matches[i - 1][j - 1]`.
3. Return `matches[m][n]`.

### Correctness

The same case analysis as above, applied to the last item of the pattern prefix and the last letter of the string prefix. Row 0 handles the empty string: only patterns made of starred items match it, which the star rule produces from `matches[0][0]`. Every cell reads cells in earlier rows or earlier columns of the same row, so row-major order is valid.

### Complexity

- Time: O(m * n) — constant work per cell.
- Space: O(m * n) — the full table.

### Trade-offs

No recursion and a fixed amount of work; it fills every cell even when the answer is decided early.

### Pitfalls and edge cases

- Row 0 must be computed with the same rules (start `i` at 0), not left all false: `matches[0][2]` is true for `p = "a*"`.
- In the star rule, compare `s[i - 1]` with the starred item `p[j - 2]`, not with `*`.

### Language notes

- Python and TypeScript: nested boolean arrays; Java and Kotlin: primitive boolean arrays with a small `fits` helper for "letter or dot".
- Go and Rust: the same `fits` helper on bytes. A `*` never starts the pattern, so `j >= 2` whenever `p[j - 1]` is a star; a violated constraint would make `j - 2` panic on a Rust `usize` instead of reading a wrong cell. `i > 0` is tested before `s[i - 1]`.

## Approach: rolling-array (Two rows over the pattern)

### Intuition

Row `i` of the table reads row `i - 1` (for `matches[i - 1][j]` and `matches[i - 1][j - 1]`) and earlier cells of row `i` itself (for `matches[i][j - 2]`). Two rows, swapped after each letter of `s`, hold everything needed.

### Algorithm

1. For each `i` from 0 to `m`: set `current[0]` to whether `i == 0`, then fill `current[j]` from `previous` and `current` with the tabulation rules; swap the rows.
2. Return `previous[n]`.

### Correctness

Invariant: after processing `i`, `previous[j]` equals `matches[i][j]` of the full table. The update reads `previous` for row `i - 1` and `current[j - 2]`, which was already written for row `i`. `current[0]` is reset every row, because only the empty string matches the empty pattern.

### Complexity

- Time: O(m * n) — the same cells as the table.
- Space: O(n) — two rows as long as the pattern.

### Trade-offs

The memory-lean standard answer. A single row does not work as directly, because the star rule needs both `matches[i - 1][j]` (old value) and `matches[i][j - 2]` (new value), and the plain rule needs the old `matches[i - 1][j - 1]`; two rows keep this simple.

### Pitfalls and edge cases

- Reset `current[0]` on every row; a reused array still holds the value from two rows ago.
- Every `current[j]` with `j >= 1` must be overwritten, including with false.

### Language notes

- Python: a fresh list per row; TypeScript: a destructuring swap of two arrays; Java: an explicit swap; Kotlin: `previous = current.also { current = previous }`.
- Go: `previous, current = current, previous` swaps the slice headers; Rust: `std::mem::swap`. Neither row needs clearing: every cell of `current` is rewritten for each row, and row 0 never reads `previous`.
