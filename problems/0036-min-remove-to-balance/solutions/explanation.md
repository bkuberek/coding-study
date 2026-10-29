# Minimum Removals to Balance Parentheses: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rescan-delete | brute | O(n^2) | O(n) | short strings, or as a correctness oracle |
| stack | optimal | O(n) | O(n) | default answer; easiest to argue correct |
| two-pass | optimal | O(n) | O(n) | no positions to store; counters only |

All approaches delete exactly the parentheses that a left-to-right scan cannot match: every `)` that arrives while nothing is open, and as many `(` as are still open at the end. That number is a lower bound for any answer (each such `)` has no `(` before it to pair with, and the leftover `(` have no `)` after them), and deleting that many is always enough, so it is the minimum. The approaches differ only in which of the leftover `(` they pick; the checker accepts any balanced result with the minimum number of deletions.

## Approach: rescan-delete (Delete the first offending parenthesis and rescan)

### Intuition

Find one parenthesis that certainly has to go, delete it, and start over. Scanning left to right, the first `)` that arrives with nothing open is such a parenthesis. If there is none but some `(` stay open, scanning right to left finds an opener with no closer available after it.

### Algorithm

1. Repeat:
   1. Scan left to right with a depth counter. If a `)` arrives at depth 0, delete it and restart.
   2. If the scan ends at depth 0, return the string.
   3. Otherwise scan right to left counting `)`; the first `(` met while that count is 0 has no closer left. Delete it and restart.

### Correctness

Each deleted parenthesis belongs to the minimal set described above: the first `)` at depth 0 can never be matched, and the `(` found by the backward scan has every `)` after it already paired with an opener between them, so deleting it leaves every prefix balance at least 0 and reduces the final depth by one. Each deletion therefore lowers the minimum number of remaining deletions by exactly one, and the loop stops when the string is balanced, after exactly the minimum number of deletions.

### Complexity

- Time: O(n^2) — each deletion costs a scan and a rebuild of O(n). The generated strings need between n/20 and n/10 deletions, so the work grows with n^2 at every seed.
- Space: O(n) — the rebuilt string.

### Trade-offs

Each step is easy to justify, which makes it a good oracle. It rediscovers the same depths on every scan; one pass that remembers them, the stack, does all the work at once.

### Pitfalls and edge cases

- Deleting the first `(` instead of one without a closer after it can break a pair that was fine: in `()(`, deleting index 0 leaves `)(`, which is still unbalanced.
- Letters are never deleted; the scans skip them.

### Language notes

- Python: string slicing rebuilds the string on every deletion; the walrus operator in the `while` condition keeps the loop short.
- TypeScript: `slice` rebuilds the string, like Python.
- Java: `StringBuilder.deleteCharAt` deletes in place by shifting the tail, still O(n) per deletion.
- Kotlin: the same `StringBuilder.deleteCharAt`; `text.indices.reversed()` walks backwards.
- Go: the text is a `[]byte`, and `slices.Delete(text, p, p+1)` removes one byte in place by shifting the tail, which is still O(n) per deletion. The input is ASCII, so bytes are characters.
- Rust: the text is a `Vec<char>`; `Vec::remove` shifts the tail, O(n) per deletion, and `into_iter().collect::<String>()` rebuilds the string at the end. The helper takes `&[char]` and returns `Option<usize>` instead of -1.

## Approach: stack (Stack of unmatched opening positions)

### Intuition

Scan once, pushing the position of every `(`. A `)` matches the most recent unmatched `(`, so pop it; a `)` that finds the stack empty is deleted. At the end, the positions left on the stack are the openers that were never closed: delete them too.

### Algorithm

1. Mark nothing as deleted; start with an empty stack of positions.
2. For each position `i`:
   1. On `(`, push `i`.
   2. On `)`, pop if the stack is non-empty; otherwise mark `i` as deleted.
3. Mark every position still on the stack as deleted.
4. Return the characters that are not marked, in order.

### Correctness

Matching each `)` with the most recent unmatched `(` is the standard way to pair parentheses, and it pairs as many as possible: a `)` is left unmatched only when no `(` before it is free. So the deleted `)` are exactly the unmatched closers, and the positions left on the stack are exactly the openers still open at the end, which together form a minimal deletion set. The remaining parentheses are the matched pairs, which nest properly, so the result is balanced.

### Complexity

- Time: O(n) — one scan, one pass over the stack and one pass to build the result.
- Space: O(n) — the stack of positions and the deletion marks.

### Trade-offs

Linear, simple, and its correctness argument is the cleanest. It stores up to n positions; the two-pass version needs only a counter and the output buffers. Among the possible answers, it deletes the leftover openers that were opened earliest without being closed.

### Pitfalls and edge cases

- Do not delete while scanning by building a new string per deletion; that brings back the quadratic cost. Mark first, build once.
- A string of letters only, or an already balanced string, is returned unchanged.

### Language notes

- Python: deleted characters are replaced by `""` in a list, so one `"".join` produces the result.
- TypeScript: a boolean array of marks and one pass that appends kept characters.
- Java: `ArrayDeque<Integer>` holds positions; iterating it at the end marks the leftovers, in any order.
- Kotlin: `kotlin.collections.ArrayDeque<Int>` for positions; `filterIndexed` builds the result string in one call.
- Go: a `[]bool` marks deleted positions and a `[]int` holds the open positions; `string(result)` converts the kept bytes at the end.
- Rust: `open_positions.pop().is_none()` pops the matching opener and detects an unmatched closer in one expression. The result is `s.chars().zip(deleted).filter(..).map(..).collect()`, one pass with no index arithmetic.

## Approach: two-pass (Two passes with an open counter)

### Intuition

The first pass, left to right, deletes every `)` that finds nothing open and counts how many `(` remain open at the end. The second pass, right to left, deletes that many `(` starting from the right: the last openers of the string have the fewest closers after them.

### Algorithm

1. Left to right, keep a counter `open`. Skip a `)` when `open` is 0; otherwise update `open` and keep the character.
2. Right to left over the kept characters, skip each `(` while `open` is positive (decrementing it), and keep everything else.
3. Reverse the second pass's output and return it.

### Correctness

After pass 1, no prefix of the kept string has more `)` than `(`, and exactly `open` openers are unmatched. Pass 2 deletes the last `open` openers. Take any prefix ending at position `t`. If `t` lies before the first deleted opener, its balance is unchanged and at least 0. Otherwise every `(` after the first deleted one is deleted, so the balance of the prefix equals the final balance, 0, plus the number of `)` after `t`, which is at least 0. So the result is balanced, and it deletes exactly the minimum number of parentheses.

### Complexity

- Time: O(n) — two linear passes and a reversal.
- Space: O(n) — the kept characters and the output; only a counter besides.

### Trade-offs

Same bounds as the stack with no positions to store, at the price of a slightly subtler argument for the second pass. It returns a different, equally valid answer: it deletes the rightmost leftover openers, where the stack deletes the earliest unclosed ones.

### Pitfalls and edge cases

- Pass 2 must run from the right. Deleting the first `open` openers from the left can unbalance the string: in `()(`, the leftover count is 1, and deleting the first `(` leaves `)(`.
- The second pass builds the result backwards; reverse it before returning.

### Language notes

- Python: `reversed(kept)` iterates backwards without copying; the result is reversed again when joined.
- TypeScript: collect into an array, then `reverse().join("")`.
- Java: `StringBuilder.reverse()` reverses the second pass's output in place.
- Kotlin: `kept.indices.reversed()` walks backwards; `StringBuilder.reverse()` restores the order.
- Go: `slices.Reverse` reverses the second pass's output in place.
- Rust: a match guard (`')' if open_count == 0 => continue`) expresses the first pass's rule directly, and `result.iter().rev().collect::<String>()` restores the order while it builds the final string.
