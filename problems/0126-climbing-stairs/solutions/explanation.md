# Climbing Stairs: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n) | O(n) | you think top-down and want the recurrence to stay visible in the code |
| tabulation | intermediate | O(n) | O(n) | you want the plain table first, before squeezing memory |
| two-variables | optimal | O(n) | O(1) | default answer |

All three compute the same recurrence. Let `ways(k)` be the number of move sequences that end exactly on step `k`. The last move onto step `k` is either a single step from `k - 1` or a double step from `k - 2`, and those two groups of sequences never overlap, so

`ways(k) = ways(k - 1) + ways(k - 2)`, with `ways(0) = 1` (the empty sequence) and `ways(1) = 1`.

This is the Fibonacci sequence shifted by one: `ways(n) = F(n + 1)`.

The naive version of this recursion, without any memory, is the starting point of the progression and is not a separate reference here. It calls `ways(k - 1)` and `ways(k - 2)` from every call, so the call tree has about `2 * F(n + 1)` nodes: roughly 2.7 million calls for `n = 30` and 3.7 billion for `n = 45`. That exponential growth, about 1.618 to the power `n`, is why it is described here instead of being run on the test cases.

## Approach: memoization (Top-down recursion with a memo)

### Intuition

The naive recursion is slow only because it solves the same subproblem again and again: `ways(n - 2)` is computed once inside `ways(n - 1)` and once more directly, and the duplication compounds all the way down. There are only `n + 1` distinct subproblems, so remembering each answer the first time it is computed turns the exponential call tree into a chain of `n` real computations.

### Algorithm

1. Define `ways(step)`: return 1 when `step <= 1`.
2. Otherwise, if the memo already holds a value for `step`, return it.
3. Else compute `ways(step - 1) + ways(step - 2)`, store it in the memo and return it.
4. Return `ways(n)`.

### Correctness

By strong induction on `step`. The base cases are right: there is one way to stand on the ground and one way to reach step 1. For `step >= 2`, every sequence ending on `step` has a last move of size 1 or 2; removing that move leaves a sequence ending on `step - 1` or `step - 2`, and this is a bijection, so the count is the sum of the two smaller counts, which the induction hypothesis says the recursive calls return. The memo only stores values the function would have returned anyway, so it does not change any result.

### Complexity

- Time: O(n) — each `step` from 2 to `n` is computed once; every later request for it is an O(1) memo lookup, and each computation makes two calls.
- Space: O(n) — the memo has `n + 1` entries and the recursion is up to `n` frames deep.

### Trade-offs

Closest to how the problem is usually reasoned about, so it is a natural first answer in an interview. It pays for the recursion with stack frames and call overhead; for large `n` in a language with a small default stack, the depth itself can become the problem, which the bottom-up versions avoid.

### Pitfalls and edge cases

- The memo must be created once per top-level call. A module-level cache in Python survives across calls; that is harmless here because the answer depends only on `step`, but it is a trap in problems where the subproblem also depends on the input array.
- Using 0 as "not computed" works because every real count is at least 1. In problems where 0 is a legal answer, use a separate sentinel such as -1 or a nullable entry.
- Forgetting the base case `step <= 1` (rather than `step == 1`) makes `ways(0)` recurse into negative steps.

### Language notes

- Python: `functools.cache` on a nested function gives each call of `climb_stairs` its own memo. The Python runner raises the recursion limit, but with `n <= 45` the depth is tiny anyway.
- TypeScript: a closure over an array filled with 0; arrow functions capture `memo` without passing it.
- Java: a private helper takes the memo array as a parameter, since Java has no nested functions.
- Kotlin: a local `fun` inside `climbStairs` captures the `IntArray` memo directly.

## Approach: tabulation (Bottom-up table of step counts)

### Intuition

The recursion only ever asks for smaller steps, so the subproblems can be solved in increasing order of `step`. When the loop reaches `step`, both values it needs are already in the table: no recursion and no "is it computed yet" checks.

### Algorithm

1. Create `ways` of length `n + 1`; set `ways[0] = 1` and `ways[1] = 1`.
2. For `step` from 2 to `n`, set `ways[step] = ways[step - 1] + ways[step - 2]`.
3. Return `ways[n]`.

### Correctness

Loop invariant: before the iteration for `step`, `ways[k]` holds the correct count for every `k < step`. It holds initially for `k = 0` and `k = 1`. The iteration fills `ways[step]` from two correct entries using the recurrence proved in the memoization section, so the invariant holds for `step + 1`. After the loop, `ways[n]` is correct.

### Complexity

- Time: O(n) — one constant-time addition for each step from 2 to `n`.
- Space: O(n) — the table has `n + 1` entries.

### Trade-offs

As fast as memoization without recursion overhead or stack depth, and it is the simplest to verify, which makes it the oracle. It still stores the whole table even though each entry is read only by the next two iterations.

### Pitfalls and edge cases

- Size the table `n + 1`, not `n`: the answer lives at index `n`.
- With `n = 1` the table still needs index 1, so allocate before assigning `ways[1]`; a table of length `n` would overflow at `n = 1`.

### Language notes

- Python: `[0] * (n + 1)` is safe here because the elements are immutable integers.
- TypeScript: `new Array<number>(n + 1).fill(0)`; without `fill` the entries are holes and arithmetic on them gives `NaN`.
- Java and Kotlin: `new int[n + 1]` and `IntArray(n + 1)` are zero-initialized primitive arrays.

## Approach: two-variables (Rolling pair of counts)

### Intuition

Each entry of the table is read only by the next two iterations. Keeping just the last two counts, and sliding them up one step per iteration, computes the same values in constant memory.

### Algorithm

1. Set `twoBelow = 1` and `oneBelow = 1`: the counts for steps 0 and 1.
2. Repeat for each step from 2 to `n`: the new count is `oneBelow + twoBelow`; then `twoBelow` takes the old `oneBelow`, and `oneBelow` takes the new count.
3. Return `oneBelow`.

### Correctness

Invariant: before the iteration for `step`, `twoBelow = ways(step - 2)` and `oneBelow = ways(step - 1)`. It holds for `step = 2`. The iteration computes `ways(step)` by the recurrence and shifts the pair, so the invariant holds for `step + 1`. When the loop ends after `step = n`, `oneBelow = ways(n)`; when `n = 1` the loop does not run and `oneBelow = ways(1) = 1`.

### Complexity

- Time: O(n) — one addition and two assignments per step.
- Space: O(1) — two integers, whatever the value of `n`.

### Trade-offs

The answer interviewers expect after the table. It hides the recurrence a little, so say the table version out loud first. A closed form (Binet's formula) or 2x2 matrix exponentiation reaches O(log n) time, but with `n <= 45` that buys nothing and floating-point rounding makes Binet's formula fragile.

### Pitfalls and edge cases

- Update the pair simultaneously. Writing `twoBelow = oneBelow` before computing the sum loses the old value; compute the new count into a temporary first (or use tuple assignment).
- The answer for `n = 45` is 1836311903, just under 2^31 - 1; one more step would overflow a 32-bit integer, so the constraint is tight on purpose.

### Language notes

- Python and TypeScript: tuple and array destructuring swap the pair in one statement.
- Java: a temporary `current` makes the simultaneous update explicit.
- Kotlin: `repeat(n - 1)` runs the body once per step from 2 to `n`, and zero times when `n = 1`.
