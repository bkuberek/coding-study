# Valid Palindrome: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| filter-reverse | brute | O(n) | O(n) | clarity matters more than memory, or as a correctness oracle |
| two-pointers | optimal | O(n) | O(1) | default answer; the interviewer asks for constant extra memory |

## Approach: filter-reverse (Clean copy compared with its reverse)

### Intuition

The definition already describes an algorithm: keep the letters and digits, lowercase them, and check that the result equals its own reverse. Doing exactly that, in two separate steps, is hard to get wrong.

### Algorithm

1. Walk `s` once and collect every character that is a letter or a digit, lowercased, into a new sequence `cleaned`.
2. Build the reverse of `cleaned`.
3. Return whether `cleaned` and its reverse are equal.

### Correctness

Step 1 produces exactly the sequence the statement defines: the kept characters in their original order with case removed. A sequence is a palindrome precisely when it equals its reverse, because position `i` of the reverse holds position `len - 1 - i` of the original. An empty `cleaned` equals its empty reverse, so a line with no letters or digits returns `true`, as required.

### Complexity

- Time: O(n) — one pass to filter, one to reverse and one to compare, each over at most n characters.
- Space: O(n) — `cleaned` and its reverse each hold up to n characters.

### Trade-offs

It is the most readable version and maps one-to-one onto the definition, which is why it serves as the oracle. It always processes the whole string, even when the first and last characters already differ, and it allocates two copies. Both costs are linear, so at n = 2 * 10^5 it is still fast; the difference is memory and the lack of an early exit. In an interview, mention it as the baseline and move on to the in-place scan.

### Pitfalls and edge cases

- Lowercase before comparing, not after reversing only one side: `Xx` must be `true`.
- Digits are kept. `Never odd or even 1` is `false` because of the trailing `1`.
- A string of only ignored characters, such as ` ;-) `, is `true`, not an error.
- Do not use a case-insensitive comparison that also folds digits and symbols, for example comparing codes modulo 32: `1` (49) and `Q` (81) differ by exactly 32.

### Language notes

- Python: `str.isalnum` and `str.lower` work per character; a list comprehension builds `cleaned`, and `cleaned[::-1]` reverses it. Comparing two lists of one-character strings is element-wise.
- TypeScript: lowercase first, then strip with the regular expression `/[^a-z0-9]/g`. Strings have no `reverse`, so spread into an array, reverse and join.
- Java: `StringBuilder.reverse()` reverses in place, so take `toString()` of the forward version before calling it.
- Kotlin: `String.filter`, `lowercase()` and `reversed()` chain naturally; `==` on strings compares content.
- Go: strings are immutable byte sequences, so the code appends the kept bytes to a `[]byte` and builds the reverse with `slices.Clone` and `slices.Reverse`; `slices.Equal` compares them. The `unicode` package would also classify non-ASCII letters, so two small ASCII helpers do the filtering and the case folding.
- Rust: `chars()` with `char::is_ascii_alphanumeric` keeps only ASCII letters and digits, `to_ascii_lowercase` folds the case, and `cleaned.iter().eq(cleaned.iter().rev())` compares the sequence with its reverse without building the reversed copy.

## Approach: two-pointers (Converging pointers that skip ignored characters)

### Intuition

A palindrome check only ever compares the k-th kept character from the left with the k-th kept character from the right. Two indices, one starting at each end, can find those characters directly in `s` by stepping over ignored characters, so no copy is needed. The first mismatch settles the answer immediately.

### Algorithm

1. Set `left = 0` and `right = len(s) - 1`.
2. While `left < right`:
   1. If `s[left]` is not a letter or digit, increase `left` and continue.
   2. Else if `s[right]` is not a letter or digit, decrease `right` and continue.
   3. Else if the two characters differ after lowercasing, return `false`.
   4. Otherwise increase `left` and decrease `right`.
3. Return `true`.

### Correctness

Invariant: at the start of each iteration, every kept character left of `left` has been matched with the kept character in the mirrored position right of `right`, and the kept characters strictly outside `[left, right]` are the same number on both sides. Skipping an ignored character keeps the invariant because it changes no kept character. When both indices sit on kept characters, they are the next unmatched pair from each end, so comparing them is exactly the next comparison of the definition: a mismatch proves the cleaned sequence is not a palindrome. When `left >= right`, at most one kept character remains unmatched (the middle one), and it matches itself, so the answer is `true`.

### Complexity

- Time: O(n) — every iteration moves `left` right or `right` left (or both), so there are at most n iterations, each O(1).
- Space: O(1) — two indices; no copy of the string.

### Trade-offs

Same linear time as the filter, but constant memory and an early exit on the first mismatch. It is slightly easier to get wrong: the skip steps and the comparison must be separate branches, or one side can run past the other. This is the version interviewers expect, and the same converging-pointer skeleton solves Palindrome With One Deletion and Two Sum on Sorted Input.

### Pitfalls and edge cases

- Skip one side per iteration and re-check the loop condition; a nested `while` that skips without checking `left < right` can step outside the string on input such as `!!`.
- Compare lowercased characters, and lowercase only letters: digits and symbols are unaffected by `lower`, which is what you want.
- The loop condition is `left < right`, not `left <= right`: the middle character of an odd-length sequence needs no partner.
- A single-character or all-ignored string never enters the comparison branch and returns `true`.

### Language notes

- Python: `str.isalnum` and `str.lower` on one-character strings. Indexing a `str` is O(1).
- TypeScript: the reference compares UTF-16 code units from `charCodeAt` against the ASCII ranges and lowercases by adding 32, which avoids allocating a one-character string per step. `/[a-z0-9]/i.test(ch)` is a shorter but slower alternative.
- Java: `Character.isLetterOrDigit` and `Character.toLowerCase` accept Unicode letters too; on printable ASCII they behave exactly like the ASCII-only checks. `charAt` avoids copying the string, unlike `toCharArray`.
- Kotlin: `Char.isLetterOrDigit()` and `lowercaseChar()` mirror the Java calls; `when` with conditions and no subject keeps the four branches flat.
- Go: indexing a string yields bytes, which are whole characters here because the input is printable ASCII. A `switch` with no subject keeps the four branches flat, and byte arithmetic (`character + ('a' - 'A')`) lowercases an uppercase letter.
- Rust: `s.as_bytes()` borrows the bytes without copying, and `u8::is_ascii_alphanumeric` and `eq_ignore_ascii_case` are the ASCII-only tests. The right pointer is stored one past the byte it reads, so an empty string does not underflow `usize`.
