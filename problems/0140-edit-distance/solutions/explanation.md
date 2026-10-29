# Edit Distance: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard answer; the table also yields the operations |
| rolling-array | optimal | O(m * n) | O(min(m, n)) | only the distance is needed |

Here m and n are the two word lengths. The state is a pair of positions, one per word, and its value is the distance between the remaining suffixes (or the prefixes before them). Plain recursion without a memo branches three ways on every mismatch; for two words with no common letter the call count grows like the Delannoy numbers, roughly 5.8^k for two words of length k, so 20 letters each already mean more than 10^14 calls. It is described here but not among the references.

The time classes use the total length of both words as n.

## Approach: memoization (Recursion over suffix pairs with a memo table)

### Intuition

Decide what happens to the first character of each suffix. If they are equal, keep both for free. Otherwise the cheapest script does one of three things first: delete `word1[i]`, insert `word2[j]` in front, or replace `word1[i]` by `word2[j]`. Each choice leaves a smaller pair of suffixes. Many choice sequences lead to the same pair, so cache each pair's distance.

### Algorithm

1. Let `solve(i, j)` be the distance between `word1[i:]` and `word2[j:]`.
2. If `word1` is exhausted, return the number of characters left in `word2` (insert them); if `word2` is exhausted, return the number left in `word1` (delete them).
3. If `word1[i] == word2[j]`, return `solve(i + 1, j + 1)`.
4. Otherwise return `1 + min(solve(i + 1, j), solve(i, j + 1), solve(i + 1, j + 1))`.
5. Cache every result; the answer is `solve(0, 0)`.

### Correctness

Consider an optimal edit script as an alignment: each character of `word1` is either deleted or aligned with a character of `word2` (kept if equal, replaced otherwise), each character of `word2` not aligned is inserted, and aligned pairs keep their order. Look at the front characters. Either `word1[i]` is deleted, or `word2[j]` is inserted, or they are aligned with each other (any other combination would cross alignments). These three cases cost 1 plus the optimum of the corresponding smaller pair, except that aligning equal characters costs 0. When the front characters are equal, aligning them is never worse than the alternatives (a standard exchange argument), which is why step 3 does not take a minimum. The base cases are forced: from an empty word the only way is inserting everything, and to an empty word deleting everything.

### Complexity

- Time: O(m * n) — at most (m + 1)(n + 1) states, each computed once from three cached values.
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m + n.

### Trade-offs

The most direct form of the recurrence and the oracle here. It may skip parts of the table when the words are similar, but it pays for recursion and keeps the full cache.

### Pitfalls and edge cases

- Empty words are valid inputs: the base cases must not index into an empty string.
- Using 0 as "not computed" is wrong; equal suffixes have distance 0.

### Language notes

- Python: a list-of-lists cache; the runner allows deep recursion, a plain script would need `sys.setrecursionlimit`.
- TypeScript: `Int16Array` rows (distances are at most 500); `Math.min` takes three arguments.
- Java: fields hold the words and the cache; `Math.min` takes two arguments, so it is nested. The local variable `delete` is allowed in Java, although it would be a reserved word in TypeScript.
- Kotlin: a local `fun` and `minOf` with three arguments.
- Go: the built-in `min` takes three arguments (Go 1.21), and the recursion is a closure declared with `var` first.
- Rust: `Ord::min` takes two, so the three candidates chain as `a.min(b).min(c)`. `word2.len() - j` cannot underflow, because `j` never exceeds the length; the distance is cast with `as i32`. The recursion is a private function over byte slices and an `Option<i32>` table.

## Approach: tabulation (Fill the table of prefix distances)

### Intuition

Use prefixes: `cost[i][j]` is the distance between `word1[:i]` and `word2[:j]`. The borders are known (`cost[i][0] = i` deletions, `cost[0][j] = j` insertions), and every other cell depends only on its upper, left and upper-left neighbors, so a row-by-row fill works.

### Algorithm

1. Create the table and fill row 0 with `0..n` and column 0 with `0..m`.
2. For each `i` from 1 and `j` from 1: if `word1[i - 1] == word2[j - 1]`, copy `cost[i - 1][j - 1]`; otherwise take `1 + min(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1])` (delete, insert, replace).
3. Return `cost[m][n]`.

### Correctness

The same case analysis as in the memoized version, applied to the last characters of the prefixes instead of the first characters of the suffixes. Row-major order computes all three neighbors before each cell.

### Complexity

- Time: O(m * n) — one constant-time step per cell.
- Space: O(m * n) — the full table.

### Trade-offs

Tight loops and no recursion, and the full table lets you walk back from `cost[m][n]` to list the actual operations, which interviewers sometimes ask for.

### Pitfalls and edge cases

- Initialize both borders; leaving them at 0 makes deletions of a whole prefix free.
- The three neighbors map to the three operations: up is a deletion, left an insertion, diagonal a replacement (or a free match).

### Language notes

- Python: explicit loops for the borders; `min` takes any number of arguments.
- TypeScript: `Int32Array` rows.
- Java: nested `Math.min`.
- Kotlin: the row initializer sets row 0 to `0..n` directly (`IntArray(n + 1) { j -> ... }`).
- Go: the first column is set while the rows are allocated, and `range cost[0]` sets the first row.
- Rust: `iter_mut().enumerate()` fills the first column and the first row without an index loop.

## Approach: rolling-array (Two rows along the shorter word)

### Intuition

Each row of the table reads only the row above and itself. Keep two rows, swap them after every row, and let the rows run along the shorter word: the distance is symmetric, because swapping the words turns every insertion into a deletion and vice versa.

### Algorithm

1. Let `shorter` be the shorter word; set `previous = [0, 1, ..., len(shorter)]`.
2. For each character `c` of the longer word, at row `i`: set `current[0] = i`, then fill `current[j]` from `previous[j - 1]`, `previous[j]` and `current[j - 1]` as in the tabulation; swap the rows.
3. Return `previous[len(shorter)]`.

### Correctness

Invariant: after row `i`, `previous[j]` equals `cost[i][j]` of the full table. Each update reads exactly the entries the recurrence needs. Reversing an edit script between the two words gives a script of the same length in the other direction, so the distance does not depend on which word is the longer one.

### Complexity

- Time: O(m * n) — the same cells as the full table.
- Space: O(min(m, n)) — two rows along the shorter word.

### Trade-offs

The memory-lean standard answer. It cannot list the operations without extra work (Hirschberg's algorithm does it in linear space). A variant with a single row and one saved diagonal value halves the memory again.

### Pitfalls and edge cases

- Set `current[0] = i` at the start of every row; it is the cost of deleting the whole prefix of the longer word.
- When the shorter word is empty, the loops leave `previous[0]` equal to the longer word's length, which is the answer.

### Language notes

- Python: a fresh `current` list per row, starting with `[i]`.
- TypeScript: `Int32Array.from({ length }, (_, j) => j)` builds the first row; a destructuring swap reuses the two arrays.
- Java: an explicit swap of two `int[]`.
- Kotlin: `IntArray(size) { it }` builds the first row, and `previous = current.also { current = previous }` swaps.
- Go: `previous, current = current, previous` swaps the slice headers without copying; `current[0] = i` is set at the top of every row, and every other cell is overwritten.
- Rust: `(0..=n as i32).collect()` builds the first row and `std::mem::swap` swaps the two vectors. `enumerate()` is zero-based, so the row number is `i + 1`, and the cells are written at `j + 1`.
