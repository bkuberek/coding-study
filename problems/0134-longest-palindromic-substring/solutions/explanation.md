# Longest Palindromic Substring: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| interval-table | intermediate | O(n^2) | O(n^2) | you want the DP view: palindromes built from shorter ones |
| expand-around-center | optimal | O(n^2) | O(1) | default interview answer |
| manacher | optimal | O(n) | O(n) | strings are long, or the interviewer asks for linear time |

The brute force checks each of the n(n + 1) / 2 substrings with a two-pointer scan, O(n^3) in total; it is the first step of the progression and is not a separate reference here. Its waste is that checking `s[i..j]` repeats the whole check of `s[i + 1..j - 1]`. The key fact for all three approaches: for `j - i >= 2`, `s[i..j]` is a palindrome exactly when `s[i] == s[j]` and `s[i + 1..j - 1]` is a palindrome. Several answers can be valid, so a checker accepts any longest palindromic substring.

## Approach: interval-table (Table of palindromic intervals by length)

### Intuition

Record the answer to "is `s[i..j]` a palindrome?" for every interval, filling intervals in order of increasing length. Each interval then needs one character comparison and one lookup of the interval strictly inside it, which is shorter and already filled.

State: `isPalindrome[i][j]` for `i <= j`. Recurrence: true when `i == j`; for length 2, true when `s[i] == s[j]`; otherwise `s[i] == s[j] and isPalindrome[i + 1][j - 1]`.

### Algorithm

1. Mark every single character as a palindrome; start with the best answer of length 1 at position 0.
2. For `length` from 2 to `n`, and every `i` with `j = i + length - 1 < n`: apply the recurrence; if `s[i..j]` is a palindrome, record it as the best so far.
3. Return the best interval.

### Correctness

By induction on the length: when intervals of length `L` are filled, every interval of length `L - 2` is final, so each entry is computed from a correct inner entry. Every palindromic interval is therefore marked. Lengths are processed in increasing order, so the last palindrome recorded has the maximum length.

### Complexity

- Time: O(n^2) — n(n - 1) / 2 intervals of length at least 2, each O(1).
- Space: O(n^2) — the boolean table, a million entries for `n = 1000`.

### Trade-offs

The clearest dynamic-programming formulation, so it is the oracle, and it answers "is this interval a palindrome?" for every interval at once, which other problems (such as minimum palindrome partitioning) need. For this question alone, its memory is wasted: the next approach finds the same answer with O(1) extra space.

### Pitfalls and edge cases

- Fill by length, not by `i` from left to right; `isPalindrome[i + 1][j - 1]` must already be known.
- Length 2 has no inner interval; handle it separately instead of reading `isPalindrome[i + 1][i]`.
- Start the answer at length 1: a string with no repeated neighbor still has single-character palindromes.

### Language notes

- Python: a list of independent lists from a comprehension; `[[False] * n] * n` would share one row.
- TypeScript: `Array.from` with a factory for independent rows.
- Java and Kotlin: `new boolean[n][n]` and `Array(n) { BooleanArray(n) }`; one megabyte for `n = 1000`.
- Go: a `[][]bool` has no 2D constructor, so each row is its own `make([]bool, n)`; a row left unallocated would be a nil slice. Indexing a `string` gives a `byte`, which is a character here because the input is ASCII.
- Rust: `vec![vec![false; n]; n]` clones the inner vector, so the rows are independent. A `String` cannot be indexed by position, so the reference reads `s.as_bytes()`; slicing `s[a..b]` at the end is safe because every offset of an ASCII string is a character boundary.

## Approach: expand-around-center (Expand from every center)

### Intuition

The recurrence says a palindrome grows from its middle outwards one character on each side. Every palindrome has a center, either a character (odd length) or the gap between two characters (even length), so there are `2n - 1` centers. From each one, expand while the two ends match; the expansion stops exactly at the longest palindrome around that center.

### Algorithm

1. For each center `c` from 0 to `2n - 2`: `left = c / 2`, `right = (c + 1) / 2` (equal for a character center, adjacent for a gap).
2. While both are in range and `s[left] == s[right]`, move `left` down and `right` up.
3. The palindrome is `s[left + 1..right - 1]`; keep it if it is the longest so far.
4. Return the longest.

### Correctness

For a fixed center, `s[left..right]` stays a palindrome as long as each newly added pair of ends matches (the recurrence), and once a pair fails, every larger interval around the same center fails too, since it contains that mismatched pair at mirror positions. So each expansion finds the longest palindrome with that center. Every palindrome has some center, so the longest overall is among those found.

### Complexity

- Time: O(n^2) — `2n - 1` centers, each expanding at most `n / 2` steps; strings like `"aaaa..."` reach that bound.
- Space: O(1) — a few indices (the returned substring is the output).

### Trade-offs

The standard answer: short, no table, and fast in practice because most expansions stop after a step or two on varied text. The worst case, a long run of one character, is still quadratic.

### Pitfalls and edge cases

- Handle even-length palindromes; forgetting the gap centers misses `"noon"`.
- The loop exits one step past the palindrome on both sides; the length is `right - left - 1`, not `right - left + 1`.
- Encoding both kinds of center as one index `c` avoids writing the expansion twice.

### Language notes

- Python: `center // 2` and `(center + 1) // 2` give the two starting positions.
- TypeScript: `>> 1` halves the non-negative center index.
- Java and Kotlin: integer division; `substring(start, end)` excludes `end`.
- Go: `left` goes down to `-1`, and `left >= 0` is tested before `s[left]`, so the short-circuit keeps the index valid. The result is a slice of `s` that shares its bytes, which is free.
- Rust: a `usize` cannot hold `-1`, so the loop keeps `left` one past the next character to compare (`bytes[left - 1]`) and tests `left > 0`. `bytes[left..right]` is then the palindrome found so far, and its length is `right - left` with no correction.

## Approach: manacher (Manacher's algorithm)

### Intuition

Expanding from every center repeats work: inside a long palindrome, the right half mirrors the left half, so a center on the right starts with at least the radius of its mirror on the left, as long as that stays inside the long palindrome. Manacher's algorithm keeps the palindrome that reaches furthest to the right and uses its mirror to skip comparisons that are already known to match. Interleaving a separator (`"ab"` becomes `"|a|b|"`) turns every palindrome into an odd-length one with a single center, so one loop handles both kinds.

### Algorithm

1. Build `t` by putting `|` around and between the characters of `s`.
2. Keep `center` and `right`, the center and right end of the palindrome reaching furthest right.
3. For each position `i` of `t`: if `i < right`, start `radius[i]` at `min(right - i, radius[2 * center - i])`; then expand while the characters at `i - radius[i] - 1` and `i + radius[i] + 1` match.
4. If `i + radius[i]` passes `right`, make `i` the new `center`.
5. For the position with the largest radius `r`, the answer is the `r` characters of `s` starting at `(position - r) / 2`.

### Correctness

Inside the palindrome `t[2 * center - right..right]`, the text around `i` mirrors the text around `2 * center - i`, so up to the boundary `right` the palindrome around `i` is at least as long as its mirror's: the initial radius is a true palindrome radius. The expansion then extends it to the true maximum, as in the previous approach. The separators make each palindrome of `s` correspond to an odd palindrome of `t` whose radius equals the original length, so the largest radius gives the answer and the index formula maps it back to `s`.

### Complexity

- Time: O(n) — every successful comparison in step 3 moves `right` forward, and `right` only grows up to `2n + 1`, so the expansions total O(n); the rest is O(1) per position.
- Space: O(n) — the transformed string and the radius array, each of length `2n + 1`.

### Trade-offs

The only linear-time answer, and worth knowing by name. It is easy to get the mirror and index arithmetic wrong under pressure, and for `n <= 1000` it is not needed; mention it after the center expansion and write it only when asked.

### Pitfalls and edge cases

- The separator must not occur in `s`; here `s` holds only letters and digits.
- Cap the mirrored radius at `right - i`; beyond the known palindrome the mirror says nothing.
- Map back with `(i - r) / 2` for the start and `r` for the length.

### Language notes

- Python: `"|".join(s)` builds the interleaved string; `max(range(...), key=radius.__getitem__)` finds the best center.
- TypeScript: `s.split("").join("|")` interleaves; the best center is tracked in the loop.
- Java: a `char[]` filled with `|`, with the characters of `s` at the odd positions.
- Kotlin: `CharArray(size) { ... }` builds the interleaved array in one expression.
- Go: a `[]byte` filled with `'|'`, with the characters of `s` copied to the odd positions; the built-in `min` (Go 1.21) picks the mirrored radius.
- Rust: `i - radius[i] - 1 >= 0` would underflow a `usize`, so the loop tests `radius[i] < i`, which says the same thing. `vec![b'|'; 2 * n + 1]` is the separator row, and `(right - i).min(radius[...])` is the mirrored radius.
