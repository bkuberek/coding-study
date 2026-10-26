# Valid Anagram: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| strike-out | brute | O(n^2) | O(n) | strings are tiny, or as a correctness oracle |
| sorting | intermediate | O(n log n) | O(n) | the alphabet is large or unknown and a one-line answer is enough |
| counting | optimal | O(n) | O(1) | default answer for a small fixed alphabet |

Here n is the length of the strings. All three start with the same shortcut: strings of different lengths are never anagrams.

## Approach: strike-out (Strike out matching letters)

### Intuition

Pair every letter of `s` with an unused copy of the same letter in `t`. If every letter finds a partner and the lengths are equal, nothing in `t` is left over, so the strings are anagrams. Marking the partner as used ("striking it out") stops a letter of `t` from being matched twice.

### Algorithm

1. If `s` and `t` have different lengths, return `false`.
2. Keep a mark per position of `t`, all unused.
3. For each letter `c` of `s`, scan `t` from the front for the first unused position holding `c`.
   1. If none exists, return `false`.
   2. Otherwise mark that position as used.
4. Return `true`.

### Correctness

Each successful step matches one letter of `s` with a distinct position of `t` holding the same letter, so after step 3 completes there is a one-to-one matching between the positions of `s` and of `t` that preserves letters. A letter-preserving bijection means every letter occurs equally often in both strings: they are anagrams. If some letter `c` of `s` finds no unused `c` in `t`, then `s` contains more copies of `c` than `t` (every copy in `t` is already matched to an earlier copy in `s`), so they are not anagrams.

### Complexity

- Time: O(n^2) — each of the n scans can pass up to n positions. Copies of a letter are consumed from left to right, so later scans start passing more and more used positions; on the generated inputs the total is about n^2/2 positions.
- Space: O(n) — the used marks (in Python, a mutable copy of `t`).

### Trade-offs

It mirrors how a person checks an anagram by hand and needs no knowledge of the alphabet, which makes it a good oracle. It is far too slow for long strings: at n = 30,000 it scans about 4.5 * 10^8 positions. Its only advantage over sorting is that it can stop at the first unmatched letter.

### Pitfalls and edge cases

- Without the used marks, `s = "aa"` and `t = "ab"` would match both `a`s to the same position and wrongly succeed.
- The length check is required: without it, `s = "ab"` and `t = "abc"` would succeed because every letter of `s` finds a partner while `c` is left over.

### Language notes

- Python: the reference copies `t` into a list and strikes a position out by overwriting it with `""`, which no letter equals. `list.index` then does the scan in C, about ten times faster than a hand-written loop, without changing the growth.
- TypeScript, Java and Kotlin: a boolean array of used marks next to the original string avoids copying characters.

## Approach: sorting (Sort both strings)

### Intuition

Anagrams contain the same letters in some order. Sorting puts the letters of any string into one canonical order, so two strings are anagrams exactly when their sorted forms are identical.

### Algorithm

1. If the lengths differ, return `false`.
2. Sort the characters of `s` and of `t`.
3. Return whether the two sorted sequences are equal.

### Correctness

Sorting is a permutation, so the sorted form of a string has exactly the same letter counts as the string. Two sorted sequences are equal exactly when they have the same letter counts, because a sorted sequence is fully determined by its letter counts (all `a`s, then all `b`s, and so on). Therefore the sorted forms are equal exactly when `s` and `t` have the same letter counts.

### Complexity

- Time: O(n log n) — two comparison sorts of n characters, then one linear comparison.
- Space: O(n) — the sorted copies of both strings.

### Trade-offs

It is short and works for any alphabet, including Unicode, as long as both strings are split into characters the same way. It is slower than counting by a log factor and needs O(n) memory, where counting needs 26 integers. It is also the building block for grouping anagrams: the sorted form is a key that all anagrams share.

### Pitfalls and edge cases

- Sorting `String` objects is impossible in Java and Kotlin: convert to a `char[]` / `CharArray` first.
- Comparing the sorted arrays with `==` in Java compares references. Use `Arrays.equals`.

### Language notes

- Python: `sorted(s)` returns a list of one-character strings; comparing two lists compares element by element.
- TypeScript: `[...text].sort().join("")` splits into code points, sorts by UTF-16 code units (correct for lowercase letters) and joins back into a string that compares with `===`.
- Java: `toCharArray()` copies, `Arrays.sort(char[])` sorts primitives, `Arrays.equals` compares contents.
- Kotlin: `toCharArray().sortedArray()` returns a sorted copy; `contentEquals` compares contents, because `==` on arrays compares references.

## Approach: counting (Letter counts in a fixed array)

### Intuition

Anagrams are exactly the strings with equal letter counts. With only 26 possible letters, a counter per letter fits in a fixed array. Count up for every letter of `s` and down for every letter of `t`; the strings are anagrams exactly when every counter ends at zero.

### Algorithm

1. If the lengths differ, return `false`.
2. Create an array `counts` of 26 zeros.
3. For each letter of `s`, increment `counts[letter - 'a']`.
4. For each letter of `t`, decrement `counts[letter - 'a']`; if it drops below zero, return `false`.
5. Return `true`.

### Correctness

After step 3, `counts[c]` is the number of times `c` occurs in `s`. In step 4, a counter below zero means `t` has more copies of that letter than `s`, so they are not anagrams. If step 4 finishes, every counter is at least zero, and the counters sum to `len(s) - len(t) = 0`; non-negative numbers that sum to zero are all zero, so every letter occurs equally often in both strings.

### Complexity

- Time: O(n) — one pass over each string, with O(1) work per letter.
- Space: O(1) — 26 counters, independent of n.

### Trade-offs

Optimal in both time and memory for a fixed small alphabet, and the expected interview answer. For a large or unknown alphabet (Unicode), replace the array with a hash map from character to count: still O(n) time, but O(k) memory for k distinct characters. The early exit in step 4 relies on the equal-length check; without it you must scan all counters at the end instead.

### Pitfalls and edge cases

- The argument that "no counter below zero means all are zero" needs equal lengths. Skipping the length check makes `s = "abc"`, `t = "ab"` pass.
- Index with `letter - 'a'`, not the raw character code, or the array needs 123 slots.
- For Unicode input, a Java or TypeScript `char` is a UTF-16 code unit, not a character: letters outside the Basic Multilingual Plane are two units. Count code points (`codePointAt`, `String.codePoints()`) in that case.

### Language notes

- Python: `ord(letter) - ord("a")` maps a letter to 0..25. `collections.Counter(s) == Counter(t)` is the idiomatic one-liner and works for any alphabet, at the cost of hashing every character.
- TypeScript: `charCodeAt(i)` reads a UTF-16 code unit without allocating; an `Int32Array(26)` starts zeroed.
- Java: `charAt(i) - 'a'` promotes `char` to `int`, so it indexes directly. `--counts[i] < 0` decrements and tests in one expression.
- Kotlin: `letter - 'a'` on two `Char`s yields an `Int`. `IntArray(26)` starts zeroed and does not box.
