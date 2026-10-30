# Vending Machine: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| state-machine | optimal | O(d a c) per sale or refund; O(1) per other operation | O(d a + s) | default answer; states are explicit and change making is exact |

Here `d` is the number of denominations, `a` the amount of change, `c` the most coins of one value in the box, and `s` the number of slots.

## Approach: state-machine (Explicit states with a change-making coin box)

### Intuition

A vending machine is the standard example of behavior that depends on state: inserting a coin means "add credit" in service, "give it back" in maintenance; asking for service mode is fine when idle but would strand a customer's money mid-purchase. Writing the state down as one enum, and guarding every method with it, makes those rules impossible to forget and easy to read.

The second idea is that money handling is its own object. The coin box knows how many coins of each value it holds and answers one question: can it pay this exact amount, and with which coins? With limited coins, taking the largest coin first can fail even when a solution exists, so the box solves the bounded coin-change problem with a small dynamic program and only removes coins once a plan exists.

### Algorithm

1. State guards: `stock` and `loadCoins` need `MAINTENANCE`. `service(true)` is allowed only from `IDLE`, `service(false)` only from `MAINTENANCE`. `insert` in `MAINTENANCE`, or of an unaccepted coin, puts the coin in the tray and returns `-1`; otherwise the coin goes into the box, the credit grows and the state becomes `HAS_CREDIT`.
2. `select(slot)`: return the first failing check among in service, slot exists, not sold out, credit covers the price. Then ask the box to pay out `credit - price`; if it cannot, return `NO_CHANGE` with nothing changed. Otherwise decrement the slot, move the change to the tray, zero the credit and go to `IDLE`.
3. `refund`: with credit, pay it out from the box (always possible, since the inserted coins are in it), move the coins to the tray and go to `IDLE`.
4. Coin box planning, denominations sorted from largest to smallest:
   1. `fewest[i][x]`: the fewest coins making `x` from denomination `i` and the smaller ones, trying every count `k` of denomination `i` up to what the box holds: `min over k of k + fewest[i + 1][x - k * coin_i]`.
   2. If `fewest[0][amount]` is impossible, there is no plan.
   3. Otherwise walk the denominations from the largest: take the largest `k` with `k + fewest[i + 1][rest - k * coin_i] == fewest[i][rest]`, and continue with the rest.
   4. Remove the planned coins from the box.

### Correctness

States: every transition in the table happens in exactly one method, and every method checks the state before acting, so no sequence of calls reaches an undefined combination (for example service mode with credit, because `service(true)` refuses while credit exists).

Change: `fewest` satisfies the recurrence of bounded coin change, because every way to pay `x` with denominations `i..` uses some count `k` of denomination `i` (at most the box holds) and pays the rest with the smaller ones. The reconstruction keeps the total at the optimum at every step, so the plan uses the fewest coins; choosing the largest feasible `k` for the largest denomination first, then the next, is exactly the tie-break of the statement. Planning before removing means a refusal leaves the box untouched.

A refund can always be paid: the coins the customer inserted are in the box and sum to the credit, so a plan exists, and the planner returns the one with the fewest coins.

### Complexity

- Time: O(d a c) per sale or refund; O(1) per other operation — the table has `d x a` cells and each tries up to `c` counts; everything else is a map lookup or an append. `collect` sorts the tray, which holds a handful of coins.
- Space: O(d a + s) — the planning table, plus the slots.

### Trade-offs

- Greedy change (largest coin first) is O(d) and correct for canonical coin systems with unlimited coins, which is why real machines often use it plus an "exact change only" light. With limited stock it refuses sales it could make; the dynamic program never does, at a cost that is negligible at these sizes.
- The State pattern (one class per state) puts each state's behavior in one place and scales to many states and events; with three states and short guards, an enum keeps the whole machine readable in one screen. Both are explicit; implicit state spread across booleans is what to avoid.
- Paying refunds with the fewest coins is consistent with change, but customers may expect their own coins back. Keeping inserted coins in an escrow until the sale completes models that, at the price of not using them as change in the same sale.

### Pitfalls and edge cases

- Check the change before dispensing; dispensing and then discovering there is no change leaves the machine in an inconsistent state.
- The inserted coins are available as change for the same sale (a 50 can pay out a 25 it just received, if it was inserted as two 25s).
- A failed `select` must leave the credit, the box and the stock unchanged.
- `service(true)` with credit must fail, or the customer's money is trapped.
- Rejected coins (unknown value, or inserted during maintenance) go to the tray, not into the box.
- Exact credit yields an empty change list, not a failure.

### Language notes

- Python: `State` is an `Enum`; the planning table uses `float("inf")` as "impossible", which adds safely to integers.
- TypeScript: a string-literal union for the state, `Infinity` for impossible cells, and `new Array(k).fill(coin)` to add `k` coins at once.
- Java: a `TreeMap` with `Comparator.reverseOrder()` keeps denominations largest first; `Optional<List<Integer>>` signals "no plan"; impossible cells use `Integer.MAX_VALUE / 2` so adding a count cannot overflow.
- Kotlin: `(0..max).minOf { ... }` fills a cell, `(max downTo 0).first { ... }` picks the largest feasible count, and `payOut` returns `List<Int>?` so `?: return "NO_CHANGE"` reads like the rule.
- Go: the state is a named `string` type with constants, and the planning table is a `[][]int` filled with the sentinel `1 << 30`, which stays far from overflow when a coin count is added to it. The built-in `min` (Go 1.21 and later) replaces `min(a, b)` calls from a helper; `sort.Reverse(sort.IntSlice(..))` sorts denominations and the tray largest first.
- Rust: "impossible" is `i32::MAX / 2`, not `i32::MAX`: this build checks integer overflow, so adding a coin count to a maximal sentinel would panic where Python's `float("inf")` is harmless. `pay_out` returns an `Option<Vec<i32>>` and uses `?` to leave early, and `std::mem::take` moves the tray out in `collect`.
