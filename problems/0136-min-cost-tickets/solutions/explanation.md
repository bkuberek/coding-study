# Minimum Cost for Tickets: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n) | O(n) | you reason from the first uncovered trip; it also works for huge calendars |
| calendar-table | intermediate | O(W) | O(W) | the calendar is short; the simplest recurrence |
| rolling-window | optimal | O(W) | O(1) | default answer for a one-year calendar |

Here `n` is the number of travel days and `W` the last travel day (at most 365). The decision structure: the earliest trip that is not yet covered needs a pass bought for some day that covers it, and buying it for that very day is never worse than buying it earlier (a pass starting earlier covers the same trips or fewer from that point on). So each step chooses one of three passes for the first uncovered trip, and the rest of the plan is the same problem on the remaining trips.

The naive recursion over those three choices, without memory, branches three ways per pass bought, up to 3 to the power `n` calls; it is the first step of the progression and is not a separate reference here.

## Approach: memoization (Top-down cheapest cover from each travel day)

### Intuition

Let `cheapestFrom(i)` be the cheapest way to cover trips `days[i], days[i + 1], ...`. Buying a pass of length `k` for day `days[i]` covers every trip before `days[i] + k`, so the plan continues from the first trip on or after that day. Only `n + 1` distinct suffixes exist, so caching them makes each cost three choices.

### Algorithm

1. `cheapestFrom(n) = 0`.
2. For each pass `(k, price)`: advance from `i` to the first index `j` with `days[j] >= days[i] + k`; the candidate is `price + cheapestFrom(j)`.
3. Cache and return the cheapest candidate; the answer is `cheapestFrom(0)`.

### Correctness

By induction from the last trip. In an optimal plan, some pass covers trip `days[i]`; by the exchange argument above, it can be taken to start on `days[i]` without increasing the cost, and then the trips it covers are exactly those before `days[i] + k`. The remaining trips form the suffix starting at `j`, which the induction hypothesis solves optimally. Trying all three passes covers every possibility.

### Complexity

- Time: O(n) — `n` suffixes, each scanning forward over at most 30 calendar days for each of three passes, a constant number of steps.
- Space: O(n) — the cache and a recursion up to `n` frames deep.

### Trade-offs

Works on travel days only, so its cost does not depend on the calendar length: it is the right shape when days can be as large as 10^9 (replace the forward scan with a binary search or a pointer). For a one-year calendar the bottom-up versions are simpler.

### Pitfalls and edge cases

- A pass of length `k` bought for day `d` covers `d` through `d + k - 1`; the first uncovered day is `d + k`, so the comparison is `days[j] < days[i] + k`.
- Do not assume longer passes cost more; the minimum over all three handles inputs like `costs = [10, 2, 3]`.

### Language notes

- Python: `functools.cache` and a `min` over the three candidates.
- TypeScript: `Infinity` seeds the minimum.
- Java: `Integer.MAX_VALUE` seeds the minimum; it is never added to, so it cannot overflow.
- Kotlin: `DURATIONS.indices.minOf { ... }` computes the cheapest candidate in one expression.
- Go: `cheapestFrom` is a closure declared with `var` first so that it can recurse; `math.MaxInt` seeds the minimum and is never added to.
- Rust: closures cannot recurse, so `cheapest_from` and `first_uncovered` are private functions that receive the days, costs and memo. `DURATIONS.iter().zip(costs)` pairs each duration with its price, and `i32::MAX` seeds the minimum without ever being added to.

## Approach: calendar-table (Bottom-up table over calendar days)

### Intuition

Index by calendar day instead of by trip. Let `cost[d]` be the cheapest way to cover every trip on days 1 to `d`. On a day without travel nothing new is needed, so `cost[d] = cost[d - 1]`. On a travel day, look at the pass that covers day `d` in an optimal plan, and assume it ends on day `d` or later: a 1-day pass leaves days up to `d - 1` to cover, a 7-day pass days up to `d - 7`, a 30-day pass days up to `d - 30`.

### Algorithm

1. Mark the travel days; set `cost[0] = 0`.
2. For `d` from 1 to `W`: if `d` is not a travel day, `cost[d] = cost[d - 1]`; else `cost[d] = min(cost[d - 1] + costs[0], cost[max(0, d - 7)] + costs[1], cost[max(0, d - 30)] + costs[2])`.
3. Return `cost[W]`.

### Correctness

By induction on `d`. If day `d` has no trip, any cover of days up to `d - 1` also covers days up to `d`. If it has one, the pass covering it in an optimal plan can be shifted so that it ends exactly on day `d` (it then covers days `d - k + 1` to `d`, which includes every trip it covered before up to day `d`), and the rest of the plan must cover the trips on days up to `d - k`. Taking the cheapest of the three options, with negative days clamped to 0, is therefore optimal.

### Complexity

- Time: O(W) — one constant-time step per calendar day.
- Space: O(W) — the table of `W + 1` costs.

### Trade-offs

The shortest code and the easiest recurrence to state, which makes it the oracle. It walks every calendar day, which is fine for 365 days and useless for a calendar of 10^9 days.

### Pitfalls and edge cases

- Clamp `d - 7` and `d - 30` at 0: early in the year a long pass covers everything so far.
- Stop at the last travel day, not 365; later days add nothing.

### Language notes

- Python and TypeScript: a set of travel days for membership tests.
- Java and Kotlin: a boolean array indexed by day is cheaper than a hash set.
- Go and Rust: a `[]bool` or `Vec<bool>` indexed by day, like the JVM. Rust's `d.saturating_sub(7)` is Python's `max(0, d - 7)` for a `usize`, which cannot go negative; Go's built-in `min` and `max` accept three arguments.

## Approach: rolling-window (Calendar days with a 30-day ring buffer)

### Intuition

The calendar recurrence never reads further back than 30 days, so a ring buffer of 30 entries, indexed by `d % 30`, can stand in for the whole table. The slot for day `d` held day `d - 30` until it is overwritten, which is exactly the value the 30-day pass needs.

### Algorithm

1. Keep `cost` of length 30, all 0, and a pointer to the next trip.
2. For each day `d` from 1 to `W`: read `previous = cost[(d - 1) % 30]`. If `d` is not the next trip, store `previous` in slot `d % 30`. Otherwise read `weekAgo` (slot `(d - 7) % 30`, or 0 when `d < 7`) and `monthAgo` (slot `d % 30` before overwriting, or 0 when `d < 30`), advance the trip pointer, and store the minimum of the three options.
3. Return the value in slot `W % 30`.

### Correctness

Invariant: after processing day `d`, the slots hold `cost[d - 29..d]` of the calendar table, each at its index modulo 30. The update for day `d` reads `cost[d - 1]`, `cost[d - 7]` and `cost[d - 30]`, all within the 30 previous days and still present (the last one is read just before its slot is reused), so it computes the same value as the table.

### Complexity

- Time: O(W) — one constant-time step per calendar day.
- Space: O(1) — 30 integers, whatever the number of days.

### Trade-offs

Same speed as the table with constant memory, at the price of modular index arithmetic. In an interview, present the table, then mention the window; the trip-indexed memoization is the better follow-up if the calendar becomes huge.

### Pitfalls and edge cases

- Read the 30-days-ago value before writing the slot for day `d`; they are the same slot.
- Before day 7 and day 30, use 0 instead of the slot, which still holds an initial or unrelated value.
- Walking the trip pointer instead of a set lookup avoids extra memory; it must only advance on travel days.

### Language notes

- Python: `%` of a negative number is non-negative, so without the `d >= 7` guard `(d - 7) % 30` would quietly read another slot; the guards make the early-year case explicit.
- TypeScript, Java and Kotlin: `%` keeps the sign of a negative operand, so `(d - 7) % 30` would be a negative index before day 7; the guards prevent it.
- Go: `%` keeps the sign of a negative operand, so the guards matter as in Java. The ring buffer is a `[30]int` array value, which needs no allocation.
- Rust: `d` is a `usize`, so `d - 7` before day 7 would panic on overflow rather than wrap or go negative; the `d >= 7` guard avoids it. The ring buffer is a `[i32; 30]` array on the stack.
