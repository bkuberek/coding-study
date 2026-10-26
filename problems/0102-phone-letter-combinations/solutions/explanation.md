# Phone Letter Combinations: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| extend-level-by-level | optimal | O(n * 4^n) | O(n * 4^n) | you like a loop over digits; easy to explain as a Cartesian product |
| backtracking | optimal | O(n * 4^n) | O(n * 4^n) | the standard depth-first template; one shared buffer |

With n digits, the answer holds the product of the keys' letter counts, at most 4^n words of n letters each, so O(n * 4^n) is also the size of the output. Both approaches produce exactly the answer with constant work per letter written.

## Approach: extend-level-by-level (Extend every partial word by each letter of the next digit)

### Intuition

After reading the first `i` digits, the words spelled so far are all combinations of their letters. Reading digit `i + 1` multiplies that list: every partial word is followed by each letter of the new digit. Start from a list holding only the empty word and repeat for every digit.

### Algorithm

1. If `digits` is empty, return an empty list.
2. Set `words = [""]`.
3. For each digit, replace `words` by `[word + letter for word in words for letter in KEYPAD[digit]]`.
4. Return `words`.

### Correctness

Invariant: after processing the first `i` digits, `words` holds every string whose `j`-th letter belongs to `digits[j]` for `j < i`, each once. It holds for `i = 0` (only the empty word). Step 3 extends each such string by each letter of the next digit: every valid string of length `i + 1` arises from its prefix of length `i` and its last letter, in exactly one way. After the last digit, `words` is the answer.

### Complexity

- Time: O(n * 4^n) — the last level builds at most 4^n words of length n; earlier levels are smaller by a factor of at least 3 each, so together they add at most half of that.
- Space: O(n * 4^n) — the final list; the previous level is discarded as soon as the next one is built.

### Trade-offs

No recursion and very short, which makes it the oracle. It keeps a whole level in memory at a time (at most twice the output), while the backtracking holds only one buffer besides the output. String concatenation copies the prefix each time, which is fine for words of at most 6 letters.

### Pitfalls and edge cases

- Empty `digits` must return `[]`; starting from `[""]` without the guard returns `[""]`.
- Use the keypad table as given: 7 and 9 have four letters, the others three.

### Language notes

- Python: a nested comprehension builds the next level in one line.
- TypeScript: `flatMap` over the words and `map` over the letters (spread from the string) builds the next level.
- Java: a `String[]` indexed by `digit - '0'` replaces a map; `List.of("")` is an immutable starting level that is never modified.
- Kotlin: `fold` threads the list of words through the digits; `getValue` fails loudly on a digit outside the table instead of returning null.

## Approach: backtracking (Fill one letter per digit depth-first)

### Intuition

A word is a choice of one letter per digit. Keep a buffer with one slot per digit; fill slot 0 with each of its letters in turn and, for each choice, fill the remaining slots the same way. When every slot is filled, the buffer spells one word.

### Algorithm

1. If `digits` is empty, return an empty list.
2. `fill(slot)`:
   1. If `slot == n`, record the buffer as a string and return.
   2. For each letter of `KEYPAD[digits[slot]]`, write it into `buffer[slot]` and call `fill(slot + 1)`.
3. Call `fill(0)` and return the words.

### Correctness

`fill(slot)` records, for the current letters in slots `0..slot-1`, every completion of the remaining slots, each once: the loop tries every letter for `slot`, and different letters give words that differ at `slot`. By induction from the last slot backwards, `fill(0)` records every word exactly once. No undo step is needed, because each slot is overwritten before it is read again.

### Complexity

- Time: O(n * 4^n) — at most 4^n leaves, each building an n-letter string; the inner nodes number fewer than the leaves times 4/3.
- Space: O(n * 4^n) — the output; the buffer and the recursion depth add O(n).

### Trade-offs

The template behind every other problem in this pattern, and it uses a single fixed-size buffer. The level-by-level version is arguably clearer for this particular problem, since there is no pruning to do: every partial word can be completed.

### Pitfalls and edge cases

- The same empty-input guard applies.
- Do not append to the buffer and forget to remove the letter; writing into a fixed slot avoids that bookkeeping altogether.

### Language notes

- Python: `"".join(letters)` builds each word from the slot list.
- TypeScript: `letters.join("")` builds each word; iterating a string with `for...of` yields its characters.
- Java: a `char[]` buffer becomes a word with `new String(letters)`, which copies it.
- Kotlin: `String(letters)` copies the `CharArray`; a local `fun` captures the buffer and the result list.
