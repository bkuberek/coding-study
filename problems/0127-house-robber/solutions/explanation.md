# House Robber: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n) | O(n) | you reason top-down from the take-or-skip choice |
| tabulation | intermediate | O(n) | O(n) | you want the table explicit, for example to reconstruct which houses were chosen |
| two-variables | optimal | O(n) | O(1) | default answer |

Every approach answers the same question for smaller and smaller streets. For each house there are only two choices: skip it, and the rest of the street is an independent smaller problem; or take it, and the next house must be skipped, which leaves the street from two houses on. The best total is the larger of the two outcomes.

The naive recursion over that choice, with no memory, is the first step of the progression and is not a separate reference here. Its call tree branches twice per house and shrinks by one or two houses per branch, so it makes about 1.618 to the power `n` calls: already around 10^20 for 100 houses. Trying every non-adjacent subset directly is the same exponential search. Remembering the answer for each starting house collapses it to `n` distinct subproblems.

## Approach: memoization (Top-down take-or-skip with a memo)

### Intuition

Let `bestFrom(h)` be the most cash obtainable from houses `h` to the end of the street. Skipping house `h` gives `bestFrom(h + 1)`; taking it gives `nums[h] + bestFrom(h + 2)`. The naive recursion recomputes `bestFrom` of the same house along many paths. A memo indexed by house computes each value once.

### Algorithm

1. Define `bestFrom(h)`: return 0 when `h` is past the last house.
2. If the memo holds a value for `h`, return it.
3. Otherwise store and return `max(bestFrom(h + 1), nums[h] + bestFrom(h + 2))`.
4. Return `bestFrom(0)`.

### Correctness

By induction from the end of the street. Past the end the only choice is the empty set, worth 0. For house `h`, every valid set of houses from `h` onwards either excludes `h`, and is then a valid set from `h + 1`, or includes `h`, and then excludes `h + 1` and is `h` plus a valid set from `h + 2`. Both cases are covered, each by its best member (induction hypothesis), so their maximum is the best overall. The memo returns only values the recursion would have computed.

### Complexity

- Time: O(n) — each of the `n` houses is evaluated once, with two memo lookups or recursive calls.
- Space: O(n) — the memo has `n` entries and the recursion is up to `n` frames deep.

### Trade-offs

It follows the decision directly and is easy to derive under pressure. The recursion depth equals the street length, which is why the constraints stop at 2000 houses: TypeScript's default stack handles that comfortably, but a street of a million houses would need the bottom-up versions.

### Pitfalls and edge cases

- The base case must cover both `h == n` and `h == n + 1`: taking the last house calls `bestFrom(n + 1)`. Testing `h >= n` handles both.
- Use a sentinel that cannot be a real answer for "not computed": 0 is a legal total (a street of empty houses), so the references use -1.

### Language notes

- Python: `functools.cache` on the nested function memoizes by `house`; the runner raises the recursion limit for deep recursions like this one.
- TypeScript: an arrow function closes over the `memo` array.
- Java: the helper receives `nums` and `memo` explicitly; `Arrays.fill(memo, -1)` sets the sentinel.
- Kotlin: a local `fun` captures `nums` and `memo`; `IntArray(n) { -1 }` initializes the sentinel in the constructor.

## Approach: tabulation (Bottom-up table over prefixes)

### Intuition

Turn the recursion around and grow the street from the left. Let `best[i]` be the most cash from the first `i` houses. The last of those houses, `nums[i - 1]`, is either skipped (`best[i - 1]`) or taken together with the best of the first `i - 2` houses. Filling `best` from left to right means both values are ready when needed.

### Algorithm

1. Create `best` of length `n + 1` with `best[0] = 0` and `best[1] = nums[0]`.
2. For `i` from 2 to `n`: `best[i] = max(best[i - 1], best[i - 2] + nums[i - 1])`.
3. Return `best[n]`.

### Correctness

Invariant: before iteration `i`, `best[k]` is optimal for the first `k` houses for every `k < i`. It holds for `k = 0` (nothing to take) and `k = 1` (take the single house, cash is never negative). An optimal set for the first `i` houses either omits house `i - 1`, and is then a valid set of the first `i - 1` houses, or contains it, and then omits house `i - 2` and is house `i - 1` plus a valid set of the first `i - 2` houses. The recurrence takes the better of the best member of each case.

### Complexity

- Time: O(n) — one comparison and one addition per house.
- Space: O(n) — the table has `n + 1` entries.

### Trade-offs

No recursion, no stack concerns, and the clearest to check, so it is the oracle. The full table is useful when the houses themselves must be reported: walk back from `best[n]`, and wherever `best[i] != best[i - 1]` house `i - 1` was taken.

### Pitfalls and edge cases

- Indexing: `best` is indexed by prefix length, `nums` by house, hence `nums[i - 1]` in the recurrence. Mixing the two conventions is the most common bug.
- A single house: the table has length 2 and the loop does not run; `best[1] = nums[0]` is the answer.

### Language notes

- Python: `[0] * (len(nums) + 1)`; integers are immutable, so the shared initial value is safe.
- TypeScript: `new Array<number>(n + 1).fill(0)` avoids holes that would make `Math.max` return `NaN`.
- Java and Kotlin: primitive arrays start at 0; `Math.max` and `maxOf` work on unboxed `int`.

## Approach: two-variables (Rolling best totals)

### Intuition

The recurrence reads only `best[i - 1]` and `best[i - 2]`. Keep those two numbers, here called `withLast` (best for the prefix so far) and `withoutLast` (best for the prefix one house shorter), and slide them forward one house at a time.

### Algorithm

1. Set `withoutLast = 0` and `withLast = 0`.
2. For each `cash` in `nums`: `current = max(withLast, withoutLast + cash)`; then `withoutLast = withLast` and `withLast = current`.
3. Return `withLast`.

### Correctness

Invariant: before processing house `i`, `withLast = best[i]` and `withoutLast = best[i - 1]` (with `best[-1]` read as 0). Processing the house computes `best[i + 1]` by the tabulation recurrence and shifts the pair, which restores the invariant for `i + 1`. Starting both at 0 is the same as treating the street as preceded by empty houses, which changes no total. After the last house, `withLast = best[n]`.

### Complexity

- Time: O(n) — constant work per house.
- Space: O(1) — two integers.

### Trade-offs

The expected final answer: linear time, constant memory, a few lines. It discards the table, so it cannot say which houses were chosen without extra bookkeeping. The same two-variable pattern solves the circular variant by running it twice, once without the first house and once without the last.

### Pitfalls and edge cases

- Update both variables from the old values: compute `current` before overwriting `withoutLast`.
- Greedy shortcuts fail: "take every other house" misses streets like `[5, 1, 1, 5]`, and "take the richest house first" misses `[2, 3, 2]`, where the two outer houses beat the middle one.

### Language notes

- Python and TypeScript: tuple and array destructuring update the pair in one statement.
- Java and Kotlin: a temporary `current` keeps the simultaneous update explicit.
