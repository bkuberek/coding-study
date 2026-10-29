# Valid Parentheses: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| pair-removal | brute | O(n^2) | O(n) | short strings, or as a correctness oracle |
| stack | optimal | O(n) | O(n) | default answer |

Both approaches rest on the same fact: a non-empty balanced string always contains an opening bracket immediately followed by its matching closer, and deleting that pair leaves a balanced string. Pair removal applies the fact literally; the stack applies it on the fly, one character at a time.

## Approach: pair-removal (Delete adjacent matching pairs until none remain)

### Intuition

Find every `()`, `[]` or `{}` that sits side by side and delete it. Deleting an innermost pair can make its neighbors adjacent, so repeat. A balanced string shrinks to nothing; any other string gets stuck with brackets left over.

### Algorithm

1. Repeat:
   1. Delete every occurrence of `()`, `[]` and `{}` from `s`.
   2. If nothing was deleted, stop.
2. Return whether `s` is now empty.

### Correctness

Deleting an adjacent matching pair never changes whether the string is balanced: the pair is balanced by itself and does not cross any other pair. If the original string is balanced and non-empty, its innermost pair is adjacent, so each pass deletes something and the process ends with the empty string. If the string is not balanced, no sequence of deletions makes it balanced, so the process gets stuck before reaching the empty string. Either way the final emptiness test gives the right answer.

### Complexity

- Time: O(n^2) — each pass costs O(n), and a nest of depth d needs at least d/3 passes, because one pass clears at most three levels (one per bracket type); d can be n/2. The test generator places a nest of depth n/10, so the passes add up to at least about d^2/3 = n^2/300 character copies.
- Space: O(n) — each pass builds a new string.

### Trade-offs

It is the way many people check brackets by hand and it is hard to get wrong, which makes it a good oracle. Each pass is a fast built-in replacement, so it is not slow on random strings, but deep nesting makes it quadratic: at n = 100,000 the generated strings need thousands of passes. It also gives no hint about where the error is.

### Pitfalls and edge cases

- Stop when a pass deletes nothing; checking for an unchanged string by length is enough, since deletions only shorten it.
- A string of odd length can never be balanced; this approach handles it without a special case.

### Language notes

- Python: `str.replace` returns a new string; comparing lengths avoids a full string comparison.
- TypeScript: `replaceAll` with a string pattern replaces literally.
- Java: `String.replace(CharSequence, CharSequence)` replaces literally; `replaceAll` would treat `()` as a regular expression and match the empty string.
- Kotlin: `fold` applies the three replacements in sequence; `String.replace(String, String)` is literal.
- Go: `strings.ReplaceAll(s, pair, "")` replaces literally and returns a new string, as Java's `String.replace` does. Go strings are immutable byte sequences, so comparing `len` before and after is a byte count, which equals the character count here because the input is ASCII.
- Rust: `str::replace` with a `&str` pattern is literal and returns a new `String`, so each round chains three replacements and rebinds `current`. `len()` counts bytes, which equals the character count for ASCII brackets.

## Approach: stack (Stack of open brackets)

### Intuition

When a closing bracket arrives, it must close the most recently opened bracket that is still open: anything opened later is nested inside and must already be closed. "Most recent first" is exactly a stack.

### Algorithm

1. Start with an empty stack.
2. For each character `c` of `s`:
   1. If `c` is an opening bracket, push it.
   2. Otherwise, if the stack is empty or its top is not the opener of `c`, return `false`; else pop it.
3. Return whether the stack is empty.

### Correctness

Invariant: after each character, the stack holds the brackets that are open at that point, in opening order, and the prefix read so far can be balanced only by closing them in reverse order. A closer that does not match the top would close a bracket while a more recently opened one is still open, or close one of the wrong kind, or close nothing, which is exactly what the rules forbid. If every closer matches, each opener is paired with the first matching closer at its nesting level; an empty stack at the end means no opener is left unmatched.

### Complexity

- Time: O(n) — each character is pushed or popped at most once.
- Space: O(n) — the stack holds up to n openers, for example when the whole string is `((((...`.

### Trade-offs

Linear and single-pass, and it can report the exact position of the first error, which pair removal cannot. For a single kind of bracket the stack collapses into a counter of open brackets, giving O(1) memory; with three kinds the stack must remember which kind is open.

### Pitfalls and edge cases

- Check for an empty stack before popping: `")"` must return `false`, not throw.
- Check the stack at the end: `"(("` never fails a match but is unbalanced.
- Counting each kind separately is not enough: `"([)]"` has matching counts and is still unbalanced.

### Language notes

- Python: a `list` is the idiomatic stack (`append`, `pop`); a dict from closer to opener avoids a chain of `if` statements.
- TypeScript: `pop()` on an empty array returns `undefined`, which never equals an opener, so the empty check comes for free.
- Java: `ArrayDeque<Character>` is the recommended stack (`push`, `pop`); the legacy `Stack` class is synchronized and slower. `pop() != openerOf(c)` compares a `Character` with a `char`, which unboxes and compares values; comparing two `Character` objects with `!=` would compare references. A `char[]` with a top index avoids boxing entirely.
- Kotlin: `kotlin.collections.ArrayDeque<Char>` with `addLast` and `removeLastOrNull()`; a null result on an empty stack never equals an opener.
- Go: a `[]rune` is the stack: `append` pushes and reslicing `openBrackets[:last]` pops. The nil slice is a valid empty stack, and `len(openBrackets) - 1` is -1 when empty, which the `last < 0` check catches before indexing. `range` over a string yields runes, and a map from closer to opener answers both "is this a closer?" and "which opener does it need?" in one lookup.
- Rust: a `Vec<char>` is the stack. `pop()` returns an `Option<char>`, so `pop() != Some(opener_of(character))` also rejects a closer on an empty stack without a separate emptiness check.
