# Generate Parentheses: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| filter-arrangements | brute | O(sqrt(n) * 4^n) | O(4^n / sqrt(n)) | as a cross-check, or to show why pruning matters |
| count-open-close | optimal | O(4^n / sqrt(n)) | O(4^n / sqrt(n)) | default answer: every string it builds is valid |

The number of valid strings is the n-th Catalan number C_n = C(2n, n) / (n + 1), which grows like 4^n / (n^1.5 * sqrt(pi)). Each has 2n characters, so the output alone is Θ(4^n / sqrt(n)). The brute force writes all C(2n, n) arrangements of the brackets, about n + 1 times more strings than it keeps.

## Approach: filter-arrangements (Write every arrangement of n opening and n closing brackets, keep the balanced ones)

### Intuition

A valid string has exactly n of each bracket, so it is one of the C(2n, n) ways to choose which positions hold `(`. Generate all of them and keep those that are correctly nested. The nesting test is the stack check from Valid Parentheses, reduced to a counter: the depth is the height a stack of unmatched `(` would have.

### Algorithm

1. For every choice of n positions out of 2n (the reference recursion places a bracket of either kind at each position while some of that kind are left):
   1. Write `(` at the chosen positions and `)` elsewhere.
   2. Scan left to right with `depth`: add 1 for `(`, subtract 1 for `)`, and reject as soon as `depth < 0`.
   3. Keep the string if the scan ends with `depth == 0`.

### Correctness

Every correctly nested string with n pairs uses n of each bracket, so it is among the arrangements, and different position sets give different strings, so each appears once. The counter test is exact: a `)` closes an open `(` exactly when the depth before it is positive, so a string is correctly nested exactly when the depth never drops below 0 and ends at 0.

### Complexity

- Time: O(sqrt(n) * 4^n) — C(2n, n) is about 4^n / sqrt(pi * n) arrangements, each written and scanned in O(n).
- Space: O(4^n / sqrt(n)) — the kept strings, C_n of length 2n; generating the arrangements needs only O(n) at a time.

### Trade-offs

A useful cross-check and the natural first idea, but it wastes most of its work: at n = 10 it writes 184,756 strings to keep 16,796. Its validity test is the useful takeaway: the depth counter is how the optimal approach decides, before writing a character, whether that character can still lead to a valid string.

### Pitfalls and edge cases

- Reject as soon as the depth goes negative; checking only the final count accepts strings like `)(`.
- Generating all 2^(2n) strings of brackets also works, but it wastes even more: the arrangements with unequal counts can never be valid.

### Language notes

- Python: `itertools.combinations(range(2 * n), n)` lists the opening positions directly.
- TypeScript: a small recursion places either bracket while some are left, which visits the same C(2n, n) arrangements without a combinations helper.
- Java: the same recursion over a `char[]`; `new String(brackets)` copies the buffer for each kept string.
- Kotlin: a local `fun` recursion writes into a `CharArray`; `String(brackets)` copies it.

## Approach: count-open-close (Add a bracket only while the prefix can still be completed)

### Intuition

Build the string from left to right and only ever write a character that keeps a valid completion possible. A `(` is fine while fewer than n have been used. A `)` is fine only while it has something to close, that is, while more `(` than `)` have been written. Every prefix built this way extends to a valid string, so nothing is ever thrown away.

### Algorithm

1. `extend(opened, closed)` with a shared buffer:
   1. If `closed == n`, record the buffer and return.
   2. If `opened < n`, append `(`, call `extend(opened + 1, closed)`, and remove it.
   3. If `closed < opened`, append `)`, call `extend(opened, closed + 1)`, and remove it.
2. Call `extend(0, 0)`.

### Correctness

Invariant: the buffer's depth is `opened - closed >= 0` and `opened <= n`, so every prefix the recursion builds is a prefix of a correctly nested string. When `closed == n`, also `opened == n` and the depth is 0, so the recorded string is valid. Conversely, any valid string is built by following its characters: each `(` occurs while fewer than n are open, and each `)` occurs while the depth is positive, so both branch conditions allow it. Different branches write different characters at the same position, so no string is recorded twice.

### Complexity

- Time: O(4^n / sqrt(n)) — every node of the recursion is a prefix of some valid string and lies on a path of length 2n to a leaf, so the work is at most 2n per leaf, over C_n leaves: O(n * C_n), which is O(4^n / sqrt(n)).
- Space: O(4^n / sqrt(n)) — the output; the buffer and the recursion depth add O(n).

### Trade-offs

Output-optimal: it does a constant amount of work per character written. It is also the standard example of pruning a backtracking search with a counter rather than with a stack. The closure-number decomposition (a string is `(` + inner + `)` + rest) gives the same strings by dynamic programming over smaller `n`, at the same cost but with more memory for the intermediate lists.

### Pitfalls and edge cases

- The condition for `)` is `closed < opened`, not `closed < n`; the latter allows prefixes like `)`.
- The base case `closed == n` already implies `opened == n`; testing `opened == n` alone would record prefixes that still need closing brackets.
- Undo each append before trying the other branch.

### Language notes

- Python: a list of characters with `append` and `pop`, joined at each leaf, avoids repeated string copies while building.
- TypeScript: the same array buffer and `join("")`.
- Java: a `StringBuilder` with `deleteCharAt(length() - 1)` undoes the last character.
- Kotlin: `StringBuilder` works the same way; `deleteCharAt` is available on the JVM.
