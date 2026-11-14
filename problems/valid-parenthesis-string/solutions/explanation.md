# Parentheses With Wildcards: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| possible-balances | brute | O(n^2) | O(n) | a correctness baseline that follows the definition |
| two-stacks | optimal | O(n) | O(n) | you think in terms of matching positions |
| balance-range | optimal | O(n) | O(1) | default answer |

Without wildcards, a string is balanced exactly when its running open count never goes negative and ends at zero. Each `*` turns that single count into several possible counts: one more, one less, or the same. Trying all 3 choices per wildcard is exponential; the progression below tracks the possible counts instead, first as a set and then as a range.

## Approach: possible-balances (Track every possible open count)

### Intuition

After reading a prefix, the only thing that matters about the choices made so far is the resulting open count. So keep the set of counts that some choice can produce, and update it character by character: `(` adds one, `)` subtracts one (dropping counts that would go negative), `*` allows all three moves.

### Algorithm

1. Start with the set `{0}`.
2. For each character, build the next set from every count `k` in the current one: `k + 1` for `(` or `*`; `k - 1` for `)` or `*` when `k > 0`; `k` for `*`.
3. If the set becomes empty, return `false`.
4. Return whether 0 is in the final set.

### Correctness

By induction on the prefix length, the set contains exactly the open counts reachable by some replacement of the wildcards in that prefix without the count ever going negative: each character's possible effects are applied to every reachable count, and a negative count is discarded because no balanced string passes through one. The whole string can be balanced exactly when 0 is reachable at the end.

### Complexity

- Time: O(n^2) — up to `n + 1` counts per character.
- Space: O(n) — the current and next sets.

### Trade-offs

A faithful dynamic program over (position, open count), easy to trust, so it is the oracle. Looking at the sets it produces reveals the shortcut: they are always contiguous ranges.

### Pitfalls and edge cases

- Drop negative counts immediately; a prefix like `)` can never be repaired by later characters.
- A wildcard has three effects, not two: forgetting "nothing" makes `"*"` and `"(*)"` fail, because turning every wildcard into a parenthesis leaves an odd number of parentheses, which can never balance.

### Language notes

- Python: a `set` of counts.
- TypeScript, Java and Kotlin: a boolean array indexed by count, rebuilt (or swapped with a second array) for each character.
- Go and Rust: two boolean slices indexed by count, swapped after each character; `clear(following)` (Go 1.21) and `following.fill(false)` reset the next table. Scanning every slot costs O(n) per character even when few counts are possible, which is what makes the approach quadratic.

## Approach: two-stacks (Match closers against open and wildcard positions)

### Intuition

Treat it as matching. Scan left to right with one stack of unmatched `(` positions and one of unused `*` positions. Each `)` should close a real `(` if one is open (wildcards are more flexible, so save them), otherwise use a wildcard as `(`, otherwise fail. At the end, each leftover `(` must be closed by a wildcard that comes after it.

### Algorithm

1. For each position: push `(` and `*` onto their stacks. For `)`, pop an open position if any, else pop a wildcard position, else return `false`.
2. While both stacks are non-empty, pop the latest `(` and the latest `*`; if the `(` comes after the `*`, return `false`.
3. Return whether no `(` is left.

### Correctness

Exchange argument for step 1: if a valid assignment closes this `)` with a wildcard while a real `(` is still open, swapping the two roles (the `(` closes this `)`, the wildcard does whatever the `(` was matched with, or becomes nothing) keeps the string balanced, so preferring the real `(` never loses a solution. Which open `(` is used does not matter for feasibility. In step 2, the latest leftover `(` is best served by the latest wildcard: if that wildcard is before it, no wildcard after it exists, so it cannot be closed. Pairing latest with latest leaves the earlier wildcards for the earlier `(`, which is optimal by the same swapping argument. Unused wildcards become nothing.

### Complexity

- Time: O(n) — each position is pushed and popped at most once.
- Space: O(n) — the two stacks.

### Trade-offs

Gives an actual matching, which is useful if the replacements themselves must be reported. It needs linear memory and a two-phase argument; the range approach is shorter.

### Pitfalls and edge cases

- In the final phase compare positions: `(*` works, `*(` does not.
- Popping from both stacks pairs the latest `(` with the latest `*`; pairing the earliest ones instead wrongly fails on `*(*`, where the first wildcard comes before the `(` but the second one can close it.

### Language notes

- Python and TypeScript: plain lists and arrays as stacks.
- Java: `ArrayDeque<Integer>` as a stack (`push` / `pop`); comparing two popped `Integer`s with `>` unboxes them.
- Kotlin: `kotlin.collections.ArrayDeque` with `addLast` / `removeLast`.
- Go: slices as stacks (`append` to push, a reslice to pop) and a tagless `switch` whose cases are conditions. Rust: `Vec<usize>` stacks and `match` arms with guards (`_ if !opens.is_empty()`). The final loop peeks with `last()` before it pops both stacks: popping the opens first would lose a `(` when no wildcard is left.

## Approach: balance-range (Keep the lowest and highest possible open count)

### Intuition

The sets of the first approach are always intervals: starting from `{0}`, every update shifts all values by one or spreads each value to its neighbors, which keeps an interval an interval. So two numbers describe the set exactly: `lowest` and `highest`. A `(` raises both, a `)` lowers both, a `*` lowers `lowest` and raises `highest`. A negative `lowest` is clamped to 0 because those choices are not allowed, and a negative `highest` means every choice has failed.

### Algorithm

1. Set `lowest = highest = 0`.
2. For each character, update both bounds as described.
3. If `highest < 0`, return `false`; otherwise set `lowest = max(lowest, 0)`.
4. Return `lowest == 0`.

### Correctness

Invariant: after each prefix, the reachable open counts are exactly the integers from `lowest` to `highest`. It holds initially. Each update maps an interval to an interval (for `*`, `[a, b]` becomes `[a - 1, b + 1]`, since the three moves from consecutive values fill every gap), and clamping removes exactly the negative counts. If `highest` drops below 0, no non-negative count remains. At the end, 0 is reachable exactly when `lowest` is 0, because `lowest` is never negative.

### Complexity

- Time: O(n) — constant work per character.
- Space: O(1) — two integers.

### Trade-offs

The expected answer: one pass, two variables. Its correctness depends on the interval argument, which is worth stating out loud; it says whether a balanced replacement exists but not which one.

### Pitfalls and edge cases

- Check `highest < 0` before clamping `lowest`, and clamp only `lowest`: `highest` going negative is a real failure.
- Return `lowest == 0`, not `highest == 0`: wildcards that can become nothing let the count be anything in the range.

### Language notes

- Kotlin: a `when` over the character with block bodies updates both bounds per branch.
- All four languages use the same two-integer loop.
- Go and Rust: a `switch` or `match` on the byte, whose last arm is the wildcard, the only other symbol the constraints allow.
