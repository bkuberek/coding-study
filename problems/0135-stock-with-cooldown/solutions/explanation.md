# Stock Trading With Cooldown: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n) | O(n) | you reason as a sequence of decisions: wait, buy or sell |
| tabulation | intermediate | O(n) | O(n) | you want the per-day states written out before rolling them |
| state-machine | optimal | O(n) | O(1) | default answer |

Without the cooldown, the greedy rule "collect every rise between consecutive days" is optimal. The cooldown breaks it: two rises separated by a single falling day (such as `1, 4, 2, 7`) cannot both be collected, and whether to merge them into one long trade or keep only one depends on the numbers. That choice is a dynamic program over a tiny state: the day, and whether a share is held (plus, for the bottom-up form, whether the share was sold today).

The naive recursion over every daily choice, without memory, branches up to twice per day: exponential, about 2 to the power `n` paths in the worst case. It is the first step of the progression and is not a separate reference here.

## Approach: memoization (Top-down over day and holding state)

### Intuition

Let `best(day, holding)` be the most profit obtainable from `day` to the end, given whether a share is held at the start of `day`. Each day offers two choices: wait, or act (buy if not holding, sell if holding). A sale makes the next day a forced rest, so after selling the decision resumes on `day + 2`. There are only `2n` distinct states, so caching them removes the exponential repetition.

### Algorithm

1. `best(day, holding) = 0` when `day >= n`.
2. Waiting gives `best(day + 1, holding)`.
3. If holding, selling gives `prices[day] + best(day + 2, false)`; otherwise buying gives `-prices[day] + best(day + 1, true)`.
4. Cache and return the larger option; the answer is `best(0, false)`.

### Correctness

By induction from the last day. Every legal plan starting at `(day, holding)` begins with one of the two choices for that day; after a sale, the cooldown rule makes the next day a rest, which is exactly what skipping to `day + 2` encodes. Each choice is followed by an optimal plan for the resulting state (induction hypothesis), so the maximum of the two is optimal. A share still held at the end contributes nothing, which matches the base case of 0.

### Complexity

- Time: O(n) — `2n` states, each computed once with O(1) work.
- Space: O(n) — the cache and a recursion up to `n` frames deep.

### Trade-offs

The state space falls out of the problem statement directly, which makes it a good first answer. The recursion depth is the number of days, so the bottom-up versions are safer for long price histories.

### Pitfalls and edge cases

- After selling, resume on `day + 2`, not `day + 1`; that single offset is the whole cooldown rule.
- Never let `best` go negative: waiting until the end is always allowed, so -1 is a safe "unknown" marker.

### Language notes

- Python: `functools.cache` keys on `(day, holding)` with a `bool` flag.
- TypeScript, Java and Kotlin: a two-row table indexed by `holding` (0 or 1) and `day`, filled with -1.

## Approach: tabulation (Bottom-up table of three daily states)

### Intuition

Describe the end of each day by one of three states: `hold` (a share is held), `sold` (a share was sold today), and `rest` (no share, and no sale today, so buying tomorrow is allowed). Each state of day `i` comes from the states of day `i - 1` through one move:

- `hold[i] = max(hold[i - 1], rest[i - 1] - prices[i])`: keep holding, or buy today after a resting day.
- `sold[i] = hold[i - 1] + prices[i]`: sell the share held yesterday.
- `rest[i] = max(rest[i - 1], sold[i - 1])`: keep resting, or this is the cooldown day after yesterday's sale.

### Algorithm

1. Set `hold[0] = -prices[0]`, `sold[0] = 0`, `rest[0] = 0`.
2. For each day `i >= 1`, apply the three recurrences above.
3. Return `max(sold[n - 1], rest[n - 1])`.

### Correctness

The three states partition all situations at the end of a day, and the only transitions the rules allow are the ones listed: buying requires yesterday to be a rest (not a sale) day, which enforces the cooldown; selling requires holding. By induction on `i`, each entry is the best profit over all legal plans ending in that state. The final answer never ends in `hold`, because an unsold share only lowers the profit. `sold[0] = 0` is not a reachable state on day 0, but it equals `rest[0]` and only feeds `rest[1]`, so it cannot create a better plan than resting.

### Complexity

- Time: O(n) — three constant-time updates per day.
- Space: O(n) — three arrays of length `n`.

### Trade-offs

Makes the state machine explicit and easy to check, which is why it is the oracle. The arrays are only read one day back.

### Pitfalls and edge cases

- `hold[i]` buys from `rest[i - 1]`, never from `sold[i - 1]`: buying the day after a sale is the forbidden move.
- Start `hold[0]` at `-prices[0]`, not 0; holding a share costs its price.
- A single day: no trade is possible, and the answer is `max(sold[0], rest[0]) = 0`.

### Language notes

- All four languages use three parallel arrays; Python lists, TypeScript arrays filled with 0, and zero-initialized `int[]` and `IntArray`.

## Approach: state-machine (Rolling hold, sold and rest totals)

### Intuition

Every state of day `i` reads only day `i - 1`, so three variables can replace the three arrays, updated together each day.

### Algorithm

1. Start with `hold = -prices[0]`, `sold = 0`, `rest = 0`.
2. For each later price, compute the three new values from the old ones and assign them together.
3. Return `max(sold, rest)`.

### Correctness

Invariant: before processing day `i`, the variables equal `hold[i - 1]`, `sold[i - 1]` and `rest[i - 1]` of the tabulation. The update applies the same recurrences to those values, so the invariant holds for the next day, and the final values give the same answer.

### Complexity

- Time: O(n) — one pass, constant work per day.
- Space: O(1) — three integers.

### Trade-offs

The expected final answer, and the pattern generalizes to the whole family of stock problems: a transaction fee subtracts from `sold`, a limit of `k` transactions adds a dimension. Derive the three-state table first; the rolling form is then mechanical.

### Pitfalls and edge cases

- Update all three from the old values. Assigning `hold` first and then using it for `sold` lets a share be bought and sold on the same day.
- The answer is at least 0: `rest` starts at 0 and never decreases.

### Language notes

- Python and TypeScript: tuple and array destructuring assign the three values simultaneously.
- Java and Kotlin: temporaries `nextHold`, `nextSold`, `nextRest` make the simultaneous update explicit.
