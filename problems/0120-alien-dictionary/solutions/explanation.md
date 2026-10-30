# Alien Dictionary: Explanation

## Overview

C is the total number of characters in `words` and U the number of distinct letters (at most 26). Both approaches read the same rules, at most one per pair of neighboring words, into a directed graph on the letters, and then topologically sort it; they differ only in the sorting technique.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| kahn | optimal | O(C + U^2) | O(U^2) | default answer: iterative, and a cycle shows up as letters left over |
| dfs-postorder | optimal | O(C + U^2) | O(U^2) | you prefer depth-first search; same graph, reversed finishing order |

## Approach: kahn (Read one rule per neighboring pair, then sort the letters by in-degree)

### Intuition

In a sorted dictionary, two neighbors first differ at some position, and there the first word's letter must come earlier in the alphabet: that is the only information the pair carries. Comparing non-neighbors adds nothing, because sortedness is transitive. Collect these rules as arrows between letters; an alphabet is valid exactly when it lists the letters in an order that respects every arrow, which is a topological order, and Kahn's algorithm finds one or detects a cycle.

### Algorithm

1. Register every letter that appears in any word.
2. For each pair of neighbors, find the first position where they differ and add the arrow `first[k] -> second[k]`. If there is no such position and the first word is longer, return `""`.
3. Count incoming arrows per letter and queue the letters with none.
4. Repeatedly dequeue a letter, append it to the answer, and decrement its targets' counts, queueing those that reach zero.
5. Return the answer if it holds every letter, else `""`.

### Correctness

A list is sorted under an alphabet exactly when every neighboring pair is in order. For a pair that differs at position `k`, that means `first[k]` ranks before `second[k]`; for a pair where one word is a prefix of the other, it means the shorter word comes first, which no alphabet can change. So an alphabet sorts the list exactly when it respects all arrows and no pair breaks the prefix rule. Kahn's algorithm outputs a letter only after all letters with arrows into it, so its output respects every arrow; and it outputs every letter exactly when the arrows have no cycle, which is exactly when some alphabet respects them all. Letters without arrows may go anywhere, and the algorithm places them as soon as it meets them.

### Complexity

- Time: O(C + U^2) — each pair comparison stops at the first difference, so reading the rules costs O(C) in total; the sort visits each letter once and checks at most U targets per letter (a matrix of U^2 entries in three of the references).
- Space: O(U^2) — at most U * (U - 1) distinct arrows, plus per-letter counters; with U at most 26 this is bounded by a constant.

### Trade-offs

Linear in the input and iterative. It is the natural choice because the two failure modes are explicit: the prefix check during reading, and leftover letters after sorting. A fixed 26-letter matrix is simpler than maps of sets in Java, Kotlin and TypeScript; Python's dictionary of sets reads more naturally there.

### Pitfalls and edge cases

- Compare only neighbors, and only up to their first difference; later letters say nothing.
- `["abc", "ab"]` is invalid even though it produces no arrow: check the prefix case explicitly.
- Include letters that appear in no rule, such as every letter of a single-word list.
- Repeated rules must not inflate the incoming counts twice: store arrows in a set or a matrix.

### Language notes

- Python: `for ... else` runs the prefix check only when the pair had no differing position. Sets iterate in an order that varies between runs, so the reference may return different valid alphabets each time; the checker accepts any of them.
- TypeScript: a 26 by 26 boolean matrix dedupes rules; `String.fromCharCode(...codes)` builds the answer.
- Java: `char - 'a'` indexes the matrix; a `StringBuilder` collects the letters.
- Kotlin: `zipWithNext()` pairs neighbors, and `first.zip(second).indexOfFirst { (a, b) -> a != b }` finds the first difference, or -1 for a prefix.
- Go: a `[26][26]bool` array holds the rules, as in the Java and TypeScript references. An array is a value, so it lives on the stack without an allocation, and scanning it in letter order makes the returned alphabet the same on every run. `word[i]-'a'` indexes it directly because a string index yields a `byte`.
- Rust: `[[bool; 26]; 26]` is the rule matrix, and the letters index it as `(byte - b'a') as usize`. `words.windows(2)` yields each pair of neighbors, `first.len().min(second.len())` replaces the `zip` that stops at the shorter word, and a rule scan in letter order makes the answer deterministic.

## Approach: dfs-postorder (Depth-first search that emits a letter after everything it must precede)

### Intuition

In a depth-first search along the arrows, a letter finishes only after every letter reachable from it has finished, that is, after every letter that must come after it. Reading the finishing order backwards therefore lists each letter before all letters that must follow it. A letter met again while it is still on the current path closes a cycle.

### Algorithm

1. Read the arrows and check the prefix rule exactly as in Kahn's approach.
2. `visit(x)`: mark `x` on the path; for each arrow `x -> y`, fail if `y` is on the path, and visit `y` if it is unvisited (failing if that fails); mark `x` done and append it to `finished`.
3. Visit every unvisited letter; if any visit fails, return `""`.
4. Return `finished` reversed.

### Correctness

For an arrow `x -> y`, `y` finishes before `x`: either `y` is visited from `x` and finishes inside that call, or `y` was already done when `x` reached it (it cannot be on the path, or a cycle would have been reported). So in reversed finishing order, `x` precedes `y` for every arrow, which is a valid alphabet. If a cycle exists, the first of its letters to be visited reaches all the others while still on the path, and following the cycle leads back to it, so the search reports the cycle.

### Complexity

- Time: O(C + U^2) — the same O(C) reading, then each letter is visited once and scans its row of U possible targets.
- Space: O(U^2) — the arrow matrix or sets, the states and a recursion depth of at most U.

### Trade-offs

Equivalent to Kahn's algorithm here; the recursion is at most 26 levels deep, so the usual stack concern does not apply. Kahn's version makes the order easier to explain step by step, and it fits better if you later want, for example, the lexicographically smallest valid alphabet (use a priority queue instead of a plain queue).

### Pitfalls and edge cases

- Reverse the finishing order; the raw post-order lists letters after the ones that must follow them.
- Use three states: a letter that is done is not a cycle, only a letter still on the path is.
- The prefix rule still has to be checked while reading; the search alone cannot see it.

### Language notes

- Python: the `state` dictionary doubles as the visited set; letters not in it are unvisited.
- TypeScript: `finished.reverse()` reverses in place before converting codes to characters.
- Java: `StringBuilder.reverse()` turns the finishing order into the answer.
- Kotlin: a local `fun` recursion captures the matrix and the states; `'a' + x` converts an index back to a letter.
- Go: `visit` is a closure over `before`, `state` and `finished`, declared with `var` first so it can recurse. The finishing order is reversed in place with a two-index swap loop before it is converted to a string.
- Rust: `visit` is a free function that takes the rule matrix by reference, the state array and the output string by mutable reference, since a closure cannot call itself. `finished.chars().rev().collect()` builds the reversed answer, which is safe for the ASCII letters.
