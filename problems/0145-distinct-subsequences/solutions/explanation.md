# Distinct Subsequences: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard bottom-up answer |
| rolling-array | optimal | O(m * n) | O(n) | default answer: one array as long as `t` |

Here m is the length of `s` and n the length of `t`. The state is a pair of positions (how much of `s` has been read, how much of `t` has been spelled), and its value is a count of occurrences. Enumerating the subsets of positions of `s` directly costs C(m, n) checks; plain recursion on the "skip or match" choice without a memo visits each occurrence and each dead end separately, which is exponential as soon as letters repeat (`"aaaa...a"` against `"aaa"` already has C(1000, 3) occurrences). Neither is among the references.

The time classes use the length of `s` as n; `t` is a tenth to a quarter as long, so the table grows like n^2.

## Approach: memoization (Recursion over suffix pairs with a memo table)

### Intuition

Look at the first character of the remaining `s`. An occurrence of the remaining `t` either does not use it (count the occurrences in the rest of `s`), or uses it to match the first character of `t`, which requires the two characters to be equal (then count the occurrences of the rest of `t` in the rest of `s`). The two groups are disjoint, so the counts add. Many paths reach the same pair of suffixes, so cache each pair.

### Algorithm

1. Let `count(i, j)` be the number of occurrences of `t[j:]` in `s[i:]`.
2. If `j == len(t)`, return 1: the empty string occurs exactly once (pick nothing).
3. If fewer characters remain in `s` than in `t`, return 0.
4. Otherwise `count(i, j) = count(i + 1, j) + (count(i + 1, j + 1) if s[i] == t[j])`, cached.
5. Return `count(0, 0)`.

### Correctness

An occurrence of `t[j:]` in `s[i:]` is a set of positions. Split the sets by whether they contain position `i`. Those that do not are exactly the occurrences in `s[i + 1:]`. Those that do must map position `i` to the first character `t[j]` (it is the smallest chosen position), so they exist only when `s[i] == t[j]`, and removing position `i` gives an occurrence of `t[j + 1:]` in `s[i + 1:]`, one to one. The base cases follow from the definition, and the length check only cuts off states whose count is 0 anyway. Each call increases `i`, so the recursion terminates.

### Complexity

- Time: O(m * n) — at most m * n cached states, each combining two values.
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m.

### Trade-offs

The direct form of the recurrence and the oracle. It recurses up to 1,000 deep and keeps the whole table; the bottom-up versions do the same work in plain loops.

### Pitfalls and edge cases

- The empty `t` occurs once, not zero times; this base case is what makes the counts start at 1.
- Counts can be large even when the answer is small, because they cover all suffix pairs; the constraints guarantee they fit in 32 bits here. In general, use 64-bit integers or a modulus.

### Language notes

- Python: a list-of-lists cache and a nested function; the runner allows the recursion depth.
- TypeScript: plain number arrays (counts stay below 2^31, far from 2^53).
- Java: fields for the strings and the cache.
- Kotlin: a local `fun`; `count(i + 1, j) + if (...) ... else 0` adds the optional term inline.
- Go: a closure declared with `var count func(i, j int) int`. Go has no conditional expression, so the optional term is added by an `if` after the first call.
- Rust: a private function over byte slices. `s.len() - i` cannot underflow, because the guard above it returns before `i` passes `s.len()`. `None` marks an unknown cell.

## Approach: tabulation (Table of occurrence counts for prefix pairs)

### Intuition

Use prefixes: `ways[i][j]` counts the occurrences of `t[:j]` in `s[:i]`. Adding the character `s[i - 1]` to the prefix of `s` either leaves an occurrence untouched (it does not use the new character) or completes one by matching the new character with `t[j - 1]`.

### Algorithm

1. Create an `(m + 1) * (n + 1)` table with `ways[i][0] = 1` for every `i` and 0 elsewhere.
2. For `i` from 1 to `m` and `j` from 1 to `n`: `ways[i][j] = ways[i - 1][j] + (ways[i - 1][j - 1] if s[i - 1] == t[j - 1])`.
3. Return `ways[m][n]`.

### Correctness

The same split as above, on the last position of the prefix instead of the first of the suffix: occurrences of `t[:j]` in `s[:i]` either avoid position `i - 1` (counted by `ways[i - 1][j]`) or use it as the match for `t[j - 1]` (counted by `ways[i - 1][j - 1]` when the characters agree). Row-major order computes row `i - 1` before row `i`.

### Complexity

- Time: O(m * n) — one addition per cell.
- Space: O(m * n) — the full table.

### Trade-offs

Straightforward loops; it stores all rows although each row reads only the previous one.

### Pitfalls and edge cases

- Column 0 must be 1 in every row, including row 0; row 0 is 0 elsewhere (an empty `s` contains no non-empty `t`).
- When `t` is longer than `s`, the table simply ends at 0.

### Language notes

- Python and TypeScript: nested arrays with an explicit loop for column 0; Kotlin sets `row[0] = 1` in the row initializer.
- Go sets `ways[i][0] = 1` while it allocates each row; Rust does it with `iter_mut()` over the rows. Both loops start at 1, so `s[i - 1]` and `t[j - 1]` stay in range and a `usize` never underflows.

## Approach: rolling-array (One array over t updated from right to left)

### Intuition

Row `i` of the table reads only row `i - 1`, and only at `j` and `j - 1`. Keep one array `ways` indexed by `j`. For each new character of `s`, update `j` from right to left: then `ways[j - 1]` still holds the previous row's value when `ways[j]` is updated, so the new character is used at most once in each new occurrence. Only positions where `t[j - 1]` equals the character change.

### Algorithm

1. Set `ways = [1, 0, ..., 0]` with length `len(t) + 1`.
2. For each character `c` of `s`, for `j` from `len(t)` down to 1: if `t[j - 1] == c`, add `ways[j - 1]` to `ways[j]`.
3. Return `ways[len(t)]`.

### Correctness

Invariant: after reading `s[:i]`, `ways[j]` equals `ways[i][j]` of the full table. For a new character, entries where `t[j - 1]` differs keep the previous row's value, matching the table's first term; entries where it agrees add the previous row's `ways[j - 1]`, which is still unmodified because the loop goes from right to left.

### Complexity

- Time: O(m * n) — n steps per character of `s`.
- Space: O(n) — one array as long as `t`.

### Trade-offs

The expected optimal answer: compact, fast, and memory-light. The right-to-left order is its one subtlety; left to right would let one character of `s` match several consecutive equal characters of `t`.

### Pitfalls and edge cases

- Update right to left. With `t = "aa"` and `s = "a"`, left to right gives 1 instead of 0.
- `ways[0]` stays 1 throughout; it is never updated.

### Language notes

- The four references share the loop; Kotlin uses `downTo`, the others a decrementing index.
- Go uses the decrementing index `for j := len(t); j > 0; j--`. Rust uses `(1..=t.len()).rev()`, which counts down without a signed index and is empty when `t` is.
