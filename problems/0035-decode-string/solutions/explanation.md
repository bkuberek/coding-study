# Decode String: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| innermost-first | brute | O(g (n + m)) | O(n + m) | small inputs, or as a correctness oracle |
| recursive | optimal | O(n + d m) | O(n + m) | the grammar reading; nesting is shallow |
| two-stacks | optimal | O(n + d m) | O(n + m) | default answer; no recursion-depth limit |

Here n is the length of `s`, m the length of the decoded string, g the number of groups and d the maximum nesting depth. A decoded character inside d nested groups is copied once per level as the groups close, hence the `d m` term; the test inputs nest at most 3 levels deep, so in practice both optimal approaches are linear in n + m.

## Approach: innermost-first (Expand the innermost group and rebuild the string)

### Intuition

An innermost group, one with no brackets inside, can be expanded directly: its content is plain letters. Expanding it produces a string with one group fewer, so repeating until no `[` remains decodes everything.

### Algorithm

1. While `s` contains `[`:
   1. Find the first `]`; the last `[` before it opens the same group, which is innermost.
   2. Read the digits just before that `[` as the count `k`.
   3. Replace `k[content]` with `content` repeated `k` times, building a new string.
2. Return `s`.

### Correctness

The first `]` closes the group whose `[` is the nearest one to its left: any `[` between them would need its own `]` earlier, contradicting that this `]` is the first. That group contains no brackets, so its expansion is exactly its content repeated `k` times. Replacing a group by its expansion does not change the decoded meaning of the whole string, and each step removes one group, so after g steps the string is fully decoded.

### Complexity

- Time: O(g (n + m)) — each of the g expansions searches and rebuilds the whole current string, whose length is at most n + m. The generated groups are small and numerous, so g grows linearly with the decoded length and the work grows with its square.
- Space: O(n + m) — the current string.

### Trade-offs

Short and easy to trust, so it serves as the oracle. It copies the entire string once per group: at 10^5 decoded characters and a few thousand groups, that is hundreds of millions of character copies, against a single pass for the other approaches.

### Pitfalls and edge cases

- Read the whole count: walk left over every digit before the `[`, so `12[ab]` repeats 12 times, not 2.
- Empty content expands to nothing: `x3[]y` is `xy`.

### Language notes

- Python: `s.index("]")` and `s.rindex("[", 0, close)` search in C; `content * count` repeats a string.
- TypeScript: `lastIndexOf("[", close)` searches backwards from `close`; `String.prototype.repeat` repeats.
- Java: `String.repeat` (Java 11+) and `Integer.parseInt(s, start, open, 10)`, which parses the count in place.
- Kotlin: `'[' in text` and `String.repeat`; strings are immutable, so each expansion builds a new one, as in the other languages.

## Approach: recursive (Recursive descent over the groups)

### Intuition

The format is a small grammar: a text is a sequence of letters and groups, and a group is a count, `[`, a text and `]`. Decode a text with a function that reads letters and, at each `[`, calls itself to decode the inner text up to the matching `]`.

### Algorithm

1. `decode(position)` reads characters from `position`:
   1. Digits accumulate into `count`.
   2. On `[`, call `decode` for the inner text, append its result repeated `count` times, and reset `count`.
   3. On `]`, stop and return the decoded text and the position after the `]`.
   4. Letters are appended as they are.
2. Return `decode(0)`.

### Correctness

By induction on nesting depth: a call started just after a `[` returns exactly the decoded content of that group and the position after its `]`, because nested groups are handled by the recursive calls (which consume their own brackets) and the first `]` the call sees itself is its own. The top-level call reads to the end of the string, so it returns the decoding of the whole input.

### Complexity

- Time: O(n + d m) — each input character is read once; every decoded character is produced once in its innermost group and copied once more for each enclosing group.
- Space: O(n + m) — the partial results, plus a call stack of depth d.

### Trade-offs

It mirrors the grammar and is the most readable answer. Its stack depth equals the nesting depth, which is harmless here (at most 20 levels), but the iterative version is safer when nesting is unbounded.

### Pitfalls and edge cases

- The callee must report where it stopped; the references share one position counter (a closure or a field) so that the caller continues after the `]`.
- Reset `count` after each group, or `2[a]3[b]` would use 23 as the second count.

### Language notes

- Python: the helper returns a `(text, position)` pair; parts are collected in a list and joined once per group.
- TypeScript: a nested `decodeGroup` closure shares `position` with its recursive calls.
- Java: the input and the position live in fields, reset by each `decodeString` call; a `StringBuilder` collects the text.
- Kotlin: a local `fun decodeGroup()` captures the `position` variable; `buildString` collects the text, and `break` inside `when` leaves the loop.

## Approach: two-stacks (Stacks of counts and partial strings)

### Intuition

Make the recursion's stack explicit. On `[`, save the count and the text built so far, then start a fresh text for the group. On `]`, the fresh text is the group's content: repeat it, append it to the saved text and continue from there.

### Algorithm

1. Keep a stack of counts, a stack of saved texts, the current text and the current count.
2. For each character:
   1. Digit: extend `count`.
   2. `[`: push `count` and the current text; start an empty text and reset `count`.
   3. `]`: pop the saved text and the count; the current text becomes the saved text followed by the current text repeated `count` times.
   4. Letter: append it to the current text.
3. Return the current text.

### Correctness

Invariant: the stacks hold, for every group opened and not yet closed, its count and the decoded text preceding its `[` within the enclosing group, and the current text is the decoded content of the innermost open group so far. Each `]` closes the innermost open group, so popping gives its count and the text before it, and the update restores the invariant for the enclosing group. At the end no group is open, and the current text is the whole decoding.

### Complexity

- Time: O(n + d m) — the same copying pattern as the recursive version.
- Space: O(n + m) — the saved texts and the stacks, at most d entries each.

### Trade-offs

Same cost as the recursion without a call-depth limit, and the version most interviewers expect. A single stack of `(count, text)` pairs works equally well.

### Pitfalls and edge cases

- Push the text built before the `[`, not after: the repeated content must be appended to the outer text, not the other way round.
- Counts with several digits must accumulate, `count = count * 10 + digit`, before the `[` arrives.

### Language notes

- Python: the current text is a list of pieces, joined once when its group closes.
- TypeScript: plain string concatenation; V8 represents concatenations as ropes, so repeated `+=` stays cheap.
- Java: two `ArrayDeque`s, one of `Integer` and one of `StringBuilder`; `toString().repeat(count)` expands the group.
- Kotlin: `kotlin.collections.ArrayDeque` with `addLast` and `removeLast`; `when` with conditions dispatches on the character kind.
