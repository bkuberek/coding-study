# Substring Search: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n * m) | O(1) | the text or the pattern is small, or as a correctness oracle |
| kmp | optimal | O(n + m) | O(m) | a guaranteed linear bound is needed, whatever the input |
| rabin-karp | optimal | O(n + m) expected, O(n * m) worst case | O(1) | many patterns of one length are searched, or a hash of each window is useful anyway |

`n` is the length of the text and `m` the length of the pattern. All three return the same list. They differ in how much of the work done at one start they reuse at the next.

## Approach: brute-force (Compare the pattern at every start)

### Intuition

Lay the pattern under the text at position 0, compare letter by letter, and stop at the first letter that differs. Then slide the pattern one position to the right and start over. A start is an occurrence exactly when all `m` letters match.

### Algorithm

1. For each start from 0 to `n - m` (no start if `m > n`):
   1. Set `offset = 0` and advance it while `offset < m` and `text[start + offset] == pattern[offset]`.
   2. If `offset == m`, append `start` to the answer.
2. Return the answer.

### Correctness

A start is reported exactly when `text[start .. start + m - 1]` equals the pattern, which is the definition of an occurrence. Every possible start from 0 to `n - m` is tried and none beyond it can fit the pattern, so no occurrence is missed. The starts are visited in increasing order, so the answer is sorted. Overlapping occurrences are found because the next start is always the very next position, never a skip past the end of a match.

### Complexity

- Time: O(n * m) — about `n - m + 1` starts, each comparing up to `m` letters. The generator uses a text of `n` letters `a` and a pattern of `a` repeated `n / 2 - 1` times followed by `b`, so that each start matches `n / 2 - 1` letters before failing: about `n^2 / 4` comparisons at every size.
- Space: O(1) — an offset and the output.

### Trade-offs

It is the shortest correct solution and it needs no extra memory, which is why it is the oracle. On typical text it is fast: a mismatch usually comes within the first letter or two. The bad case is a text and a pattern with long repeated stretches, where each start redoes comparisons that the previous start has already made. The next two approaches remove that repetition in two different ways.

### Pitfalls and edge cases

- Stop the loop at `n - m`, not at `n`, or the comparison reads past the end of the text. When the pattern is longer than the text there is no start at all.
- Report the start, not the end, of each occurrence.
- Do not skip `m` positions after a match: that loses overlapping occurrences such as `aa` in `aaaa`.

### Language notes

- Python: the explicit `while` loop keeps the reference in the same shape as the other languages; `text.startswith(pattern, start)` or a slice comparison would be faster in practice, but would hide the comparisons this approach counts.
- TypeScript, Java, Kotlin: `text[i]` or `charAt(i)` reads one character of the string. The inputs are ASCII, so every character is one letter or digit.
- Java and Kotlin build the answer in a list and copy it into an `int[]` or `IntArray`; the signature asks for a primitive array.
- Go: indexing a `string` gives a `byte`. The inputs are ASCII, so bytes are letters; for general Unicode text one would compare runes or bytes of the UTF-8 encoding, depending on what a position means. A nil slice is a valid empty answer.
- Rust: `str::as_bytes` gives a `&[u8]` that can be indexed directly. `(text.len() + 1).saturating_sub(pattern.len())` is the number of starts and does not underflow when the pattern is longer.

## Approach: kmp (Failure function that never moves back in the text)

### Intuition

When a check fails after matching `k` letters, the brute force throws those `k` letters away and slides by one. But those `k` letters are the first `k` letters of the pattern, so they are known. The only starts that can still succeed are those where a *suffix* of the matched part is also a *prefix* of the pattern. Precompute, for every prefix of the pattern, the length of its longest proper prefix that is also its suffix (its **border**). Then, on a mismatch, fall back to that border length instead of starting over, and never move back in the text.

Example: for the pattern `abcabd`, the prefix `abcab` has border `ab` (length 2). If `abcab` has matched and the next letter is not `d`, the next possible match already has `ab` matched, so the search continues from matched length 2 on the same text letter.

### Algorithm

1. Build `border`, where `border[i]` is the length of the longest proper prefix of `pattern[0..i]` that is also a suffix of it. Use the same fallback idea on the pattern itself: keep a length `k`, starting at 0; for `i` from 1: while `k > 0` and `pattern[i] != pattern[k]`, set `k = border[k - 1]`; if `pattern[i] == pattern[k]`, increase `k`; set `border[i] = k`.
2. Scan the text once with `matched = 0`. For each letter: while `matched > 0` and the letter differs from `pattern[matched]`, set `matched = border[matched - 1]`; if the letter equals `pattern[matched]`, increase `matched`.
3. When `matched == m`, an occurrence ends at this letter: append `position - m + 1`, then set `matched = border[m - 1]` so that an occurrence that overlaps this one is found.
4. Return the answer.

### Correctness

The invariant of step 2 is: after reading `text[0..p]`, `matched` is the length of the longest prefix of the pattern that is a suffix of `text[0..p]` (and less than `m`). It holds at the start. When the next letter extends the matched prefix, the new longest one is one longer. When it does not, every shorter candidate is a border of the current one, so the borders are tried from the longest to the shortest by following `border`, and the first one that the letter extends is the new longest. A full match of length `m` is an occurrence ending at `p`, and every occurrence ends at a position where the longest matching prefix has length `m`, so none is missed. After a match, the next candidates are the borders of the whole pattern, which is why `matched` becomes `border[m - 1]` and not 0. The table is built by the same argument applied to the pattern against itself.

### Complexity

- Time: O(n + m) — `matched` rises by at most one per text letter and each fallback lowers it, so the fallbacks over the whole scan cannot exceed the rises, which are at most `n`. The table is built the same way in at most `m` steps.
- Space: O(m) — the `border` table.

### Trade-offs

The only approach here with a linear bound on every input, which matters when the input is chosen by someone else, and it reads each text letter once from left to right, so it works on a stream. It costs `O(m)` extra memory and the table is the hard part to get right. The algorithm is from Knuth, Morris and Pratt, "Fast pattern matching in strings", *SIAM Journal on Computing* 6(2), 1977, pp. 323 to 350. For one-off searches in typical text, a library routine is usually the better choice.

### Pitfalls and edge cases

- After a full match, fall back to `border[m - 1]`, not to 0. With 0 the overlapping occurrences are lost (`aa` in `aaaa`).
- The fallback uses `border[matched - 1]`, the border of the prefix of length `matched`, not `border[matched]`.
- Compare the letter with `pattern[matched]` only while `matched < m`. Reset right after a full match so that the index never reaches `m`.
- The table loop starts at `i = 1`: a single letter has no proper prefix, so `border[0] = 0`.
- A pattern longer than the text finds nothing and needs no special case, but building the table is still `O(m)`.

### Language notes

- Python: `enumerate(text)` and a list for the table; a helper function builds the table.
- TypeScript: `new Array(m).fill(0)` creates the table; indexing a string gives a one-letter string, and `===` compares letters.
- Java, Kotlin: an `int[]` or `IntArray` table and `charAt` or `[]` on the strings; the answer is collected in a list first.
- Go: the table is a `[]int` made with `make`; indexing the strings gives bytes.
- Rust: the table is a `Vec<usize>` over `&[u8]`; `position + 1 - pattern.len()` is written that way to stay unsigned, and the result is converted to `i32` when it is stored.

## Approach: rabin-karp (Rolling hash of each window with a check on a match)

### Intuition

Instead of comparing letters, compare numbers. Turn the pattern into one number, its hash, and do the same for every window of `m` letters in the text. The hash of the next window can be computed from the previous one in constant time: take the contribution of the letter that leaves, shift everything by one place, and add the letter that enters. Windows with a different hash are certainly different words. A window with the same hash might be the pattern, or a different word that happens to share the hash, so check such a window letter by letter before reporting it.

### Algorithm

1. If `m > n`, return an empty answer.
2. Treat a word as a number in base `B = 131` with each letter's character code as a digit, taken modulo `P = 1_000_000_007`: `hash(w) = (w[0] * B^(m-1) + w[1] * B^(m-2) + ... + w[m-1]) mod P`.
3. Compute the hash of the pattern and of the first window. Compute `B^(m-1) mod P`, the weight of the letter that leaves.
4. For each start: if the window's hash equals the pattern's hash and the window equals the pattern letter by letter, append the start. Then, if a next window exists, update the hash: `window = ((window - text[start] * B^(m-1)) * B + text[start + m]) mod P`, keeping the remainder non-negative.

### Correctness

The update is the definition of the hash applied to the next window: removing `text[start] * B^(m-1)` leaves the hash of the remaining `m - 1` letters, multiplying by `B` shifts them up one place, and adding the new letter fills the last place. Equal words have equal hashes, so every real occurrence passes the hash test and is then confirmed by the comparison. The comparison rejects every window that only shares the hash. So the reported starts are exactly the occurrences, in increasing order.

### Complexity

- Time: O(n + m) expected, O(n * m) worst case — hashing the pattern and the first window takes `m` steps and each of the other windows takes constant time, as long as the comparison runs only when the hashes agree on a real match or a rare collision. The worst case is a text where many windows match or collide: for `aaaa...a` and `aaa`, every window is an occurrence and each costs `m` letters to confirm. The generator's inputs have no window that hashes like the pattern, so they measure the linear case.
- Space: O(1) — a few integers.

### Trade-offs

It is simple, needs no table, and the rolling hash extends to other problems: many patterns of one length can share one pass by looking each window's hash up in a set, and a hash of every window is useful for finding repeated substrings. It has no linear worst-case guarantee, unlike the failure function, and its speed relies on the hash spreading windows well. The idea is from Karp and Rabin, "Efficient randomized pattern-matching algorithms", *IBM Journal of Research and Development* 31(2), 1987, pp. 249 to 260.

### Pitfalls and edge cases

- Always confirm a hash match. Without it, the answer is wrong whenever two different windows collide. The hidden cases include words built from `Aa` and `BB`: Java documents `String.hashCode` as `s[0]*31^(n-1) + s[1]*31^(n-2) + ... + s[n-1]` using `int` arithmetic, and with base 31 the two-letter words `Aa` and `BB` both give 65 * 31 + 97 = 66 * 31 + 66 = 2112. Any two texts made of the same number of `Aa` and `BB` blocks therefore get the same base-31 hash, whatever the modulus. A solution that skips the confirmation and uses base 31 reports windows that are not occurrences.
- Keep the remainder non-negative after the subtraction: add `P` before taking `% P`. In every language here except Python the result of `%` takes the sign of the left operand (documented for JavaScript, Java, Kotlin, Go and Rust), so `-5 % P` is `-5`, and a negative hash then never equals the pattern's. In Python the result takes the sign of the right operand, so the same mistake goes unnoticed there.
- Keep products inside the integer type. With `P` near 10^9 and a factor of at most 131 a product stays below 2^53 (TypeScript) and 2^63 (the others), but a larger base or modulus would need `BigInt` or 128-bit arithmetic.
- The weight of the leaving letter is `B^(m-1)`, not `B^m`.
- The window moves only while a next window exists, or the update reads past the end of the text.

### Language notes

- Python: `pow(BASE, m - 1, MODULUS)` computes the weight by modular exponentiation, and `%` with a positive modulus returns a non-negative result, so the subtraction needs no correction; the confirmation is `text.startswith(pattern, start)`, which compares in place and, unlike a slice comparison, does not copy the window.
- TypeScript: every number is a double, which holds integers exactly up to 2^53 - 1; the products stay far below that, and the subtraction is corrected by hand. `startsWith(pattern, start)` confirms a window.
- Java, Kotlin: `long` arithmetic; `String.startsWith(prefix, offset)` confirms a window without copying it.
- Go: the language only promises that `int` is 32 or 64 bits wide, and the products here need more than 32, so the reference uses `int64` for the hash values. `strings.HasPrefix(text[start:], pattern)` confirms a window, and slicing a string does not copy it.
- Rust: `u64` with the leaving contribution added as `MODULUS - leaving` to avoid underflow; a slice comparison `text[start..start + m] == *pattern` confirms a window.
