# Longest Common Subsequence: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard answer; the table also rebuilds a subsequence |
| rolling-array | optimal | O(m * n) | O(min(m, n)) | only the length is needed and memory matters |

Here m and n are the two string lengths. The state is a pair of positions, one in each string; its value is the answer for the remaining suffixes (or the prefixes before them). Plain recursion on the recurrence, without a memo, branches twice on every mismatch and revisits the same pairs exponentially often: for two strings with no common letter it makes about C(m + n, m) calls, around 10^17 for two strings of 30 characters. It is therefore not among the references.

The time classes use the total length of both strings as n; with a balanced split the table has about n^2 / 4 cells.

## Approach: memoization (Recursion over suffix pairs with a memo table)

### Intuition

Look at the first characters of the two suffixes. If they are equal, use them: matching them never hurts. If they differ, at least one of them is not part of the answer, so drop one or the other and take the better result. The same pair of suffixes is reached along many paths, so cache each pair's answer.

### Algorithm

1. Let `solve(i, j)` be the answer for `text1[i:]` and `text2[j:]`.
2. If either suffix is empty, return 0.
3. If `text1[i] == text2[j]`, the answer is `1 + solve(i + 1, j + 1)`.
4. Otherwise it is `max(solve(i + 1, j), solve(i, j + 1))`.
5. Cache each result; return `solve(0, 0)`.

### Correctness

On a match, some longest common subsequence pairs `text1[i]` with `text2[j]`. Take any longest one: if it uses neither character, prepending the pair would make it longer, which is impossible; if it pairs `text1[i]` with a later copy of that character in `text2` (or `text2[j]` with a later copy in `text1`), re-pair it with the front character, which is the same letter. The rest of it is then a common subsequence of the two shorter suffixes. On a mismatch, a common subsequence cannot use both front characters as its first character, since they differ, so it lies entirely in one of the two smaller pairs. Every call shortens at least one suffix, so the recursion terminates; the cache stores exactly the values the recursion would recompute.

### Complexity

- Time: O(m * n) — at most (m + 1)(n + 1) distinct states, each computed once in O(1).
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m + n.

### Trade-offs

The clearest path from the definition to an efficient algorithm, and the oracle here. It pays for function calls, may visit only part of the table (an advantage when the strings are similar), and recurses up to 2,000 levels deep at the limits.

### Pitfalls and edge cases

- Caching with 0 as "unknown" is wrong: 0 is a valid answer. Use -1.
- On a match, do not also try dropping characters "just in case"; the exchange argument shows it is unnecessary, and it triples the work.

### Language notes

- Python: a list-of-lists cache and a nested function; the runner allows deep recursion, a plain script would need `sys.setrecursionlimit`.
- TypeScript: `Int16Array` rows (answers are at most 1000), and an arrow function for the recursion.
- Java: the strings and the cache live in fields, since Java has no nested functions.
- Kotlin: a local `fun` closes over the strings and the cache.

## Approach: tabulation (Fill the table of prefix answers)

### Intuition

Use prefixes instead of suffixes and fill the table in an order where every entry's dependencies are already known: `best[i][j]` (the answer for `text1[:i]` and `text2[:j]`) needs the entries above, to the left and diagonally above-left. Row 0 and column 0 represent an empty prefix and are 0.

### Algorithm

1. Create a table of `(m + 1) * (n + 1)` zeros.
2. For `i` from 1 to `m` and `j` from 1 to `n`: if `text1[i - 1] == text2[j - 1]`, set `best[i][j] = best[i - 1][j - 1] + 1`; otherwise `best[i][j] = max(best[i - 1][j], best[i][j - 1])`.
3. Return `best[m][n]`.

### Correctness

The recurrence is the mirror image of the memoized one (look at the last characters instead of the first), with the same exchange argument for a match and the same case split for a mismatch. Row-major order computes `best[i - 1][*]` and `best[i][j - 1]` before `best[i][j]`, so every lookup reads a final value.

### Complexity

- Time: O(m * n) — one constant-time step per cell.
- Space: O(m * n) — the full table.

### Trade-offs

Fast in practice (tight loops, no recursion) and the standard interview answer. Keeping the full table allows walking back from `best[m][n]` to reconstruct one longest common subsequence, which the rolling array cannot do.

### Pitfalls and edge cases

- The off-by-one between table indexes and string indexes: `best[i][j]` compares `text1[i - 1]` and `text2[j - 1]`.
- Identical strings fill the diagonal; strings with no common letter leave the table at 0.

### Language notes

- Python: `[[0] * (n + 1) for _ in range(m + 1)]` creates independent rows.
- TypeScript: `Int32Array` rows are zero-initialized.
- Java and Kotlin: `new int[m + 1][n + 1]` and `Array(m + 1) { IntArray(n + 1) }` are zero-initialized.

## Approach: rolling-array (Two rows along the shorter string)

### Intuition

Row `i` of the table reads only row `i - 1` and itself. Keep two rows and swap them after each step. Because the answer does not change when the strings are swapped, let the rows run along the shorter string.

### Algorithm

1. Let `shorter` be the shorter string and `longer` the other one; create `previous` and `current` of length `len(shorter) + 1`, filled with 0.
2. For each character of `longer`: for `j` from 1, set `current[j]` from `previous[j - 1]`, `previous[j]` and `current[j - 1]` as in the tabulation; then swap the rows.
3. Return `previous[len(shorter)]`.

### Correctness

Invariant: after processing `i` characters of `longer`, `previous[j]` equals `best[i][j]` of the full table. Each update reads exactly the three table entries the recurrence needs: `previous` holds row `i - 1`, and `current[j - 1]` was just written for row `i`. `current[0]` is never written and stays 0, the empty-prefix value. Swapping the roles of the strings maps common subsequences to common subsequences, so the answer is unchanged.

### Complexity

- Time: O(m * n) — the same cells as the full table.
- Space: O(min(m, n)) — two rows along the shorter string.

### Trade-offs

Same speed as the full table (often faster, thanks to cache locality) with a fraction of the memory. It only gives the length; reconstructing a subsequence in linear space needs Hirschberg's divide-and-conquer algorithm.

### Pitfalls and edge cases

- When reusing the swapped row, every entry from index 1 on is overwritten before it is read, and index 0 must stay 0.
- A single row with one saved diagonal value also works, but the diagonal must be saved before `current[j]` is overwritten.

### Language notes

- Python: allocating a fresh `current` list per row keeps the code obvious; the swap is a reassignment.
- TypeScript: destructuring swap `[previous, current] = [current, previous]` on two `Int32Array`s.
- Java: an explicit three-line swap of the two arrays.
- Kotlin: `previous = current.also { current = previous }` swaps without a temporary variable.
