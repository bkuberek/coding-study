# Best Time to Buy and Sell Stock: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, or as a correctness baseline |
| running-minimum | optimal | O(n) | O(1) | default answer |
| daily-gains | optimal | O(n) | O(1) | you want to connect it to maximum subarray (Kadane) |

A trade is a pair of days `buy < sell`, worth `prices[sell] - prices[buy]`. The greedy insight: for a fixed selling day, the best buying day is simply the cheapest day before it, so one pass that remembers the minimum so far evaluates the best trade for every selling day.

## Approach: brute-force (Try every buy and sell pair)

### Intuition

Enumerate every pair of days with the buy before the sell and keep the largest difference. Starting from 0 covers the "do not trade" option.

### Algorithm

1. Set `best = 0`.
2. For each `buy` and each `sell > buy`, update `best` with `prices[sell] - prices[buy]`.
3. Return `best`.

### Correctness

Every allowed trade is one pair `(buy, sell)` with `buy < sell`, and each is examined once; `best` starts at 0, the value of not trading, so the result is the maximum of 0 and every trade.

### Complexity

- Time: O(n^2) — n(n - 1) / 2 pairs.
- Space: O(1) — two loop indexes and the best value.

### Trade-offs

Obviously correct, so it is the oracle; at 10^5 days it would need about 5 * 10^9 steps, which is why the large test cases stay at a few thousand days.

### Pitfalls and edge cases

- The sell day must come strictly after the buy day; including `sell == buy` is harmless (profit 0), but `sell < buy` would let you "sell before buying".
- A single day has no pair; the loops do nothing and the answer is 0.

### Language notes

- All four languages use the same nested loops; prices are at most 10^4, so differences fit easily in 32 bits.

## Approach: running-minimum (Sell against the cheapest price so far)

### Intuition

Fix the selling day `j`. The profit `prices[j] - prices[i]` is largest when `prices[i]` is smallest over `i < j`. Keeping the minimum of the prices seen so far gives that value in O(1) for every `j`, so one pass finds the best selling day together with its best buying day.

### Algorithm

1. Set `cheapest = prices[0]` and `best = 0`.
2. For each price in order: update `best` with `price - cheapest`, then update `cheapest` with `price`.
3. Return `best`.

### Correctness

Exchange argument: take an optimal trade `(i, j)`. If some day `k < j` is cheaper than day `i`, replacing the buy day by `k` gives a trade at least as good, so there is an optimal trade whose buy day is a cheapest day before `j`. When the loop reaches day `j`, `cheapest` is exactly the minimum over days before `j` (updating it after computing the profit keeps day `j` out, and comparing with itself would only give 0 anyway), so `best` sees that optimal trade. Every value `best` takes is a real trade or 0, so it never exceeds the optimum.

### Complexity

- Time: O(n) — one pass with two comparisons per day.
- Space: O(1) — two integers.

### Trade-offs

The standard answer: one pass, constant memory, and easy to explain with the exchange argument. It is a greedy algorithm and also a tiny dynamic program (the state is the minimum of a prefix).

### Pitfalls and edge cases

- Do not pair the overall minimum with the overall maximum: the maximum may come before the minimum (`[2, 9, 1, 3]` has answer 7, not 2).
- Initialize `best` to 0, not to `prices[1] - prices[0]`, which can be negative and would also fail for a single day.

### Language notes

- Python: `max` and `min` builtins per step; iterating over the list itself avoids the copy that `prices[1:]` would make.
- TypeScript: `Math.max` and `Math.min` on numbers.
- Java and Kotlin: `Math.max` / `Math.min` and `maxOf` / `minOf` on primitive `int`.

## Approach: daily-gains (Best run of daily price changes)

### Intuition

The profit of a trade from day `i` to day `j` telescopes into the sum of the daily changes `prices[k] - prices[k - 1]` for `k` from `i + 1` to `j`. The best trade is therefore the maximum-sum run of consecutive daily changes, or 0, which is Kadane's algorithm: keep the best sum of a run ending today, and drop the run when it turns negative.

### Algorithm

1. Set `best = 0` and `endingHere = 0`.
2. For each day from the second on: `endingHere = max(0, endingHere + today - yesterday)`; update `best`.
3. Return `best`.

### Correctness

`endingHere` after day `j` is the largest profit of a trade that sells on day `j` (or 0): extending the best trade selling on day `j - 1` by one day adds today's change, and starting fresh means buying yesterday or not trading. The greedy step "drop a negative running sum" is the exchange argument of Kadane: a run with a negative sum can only lower any longer run that starts with it. The maximum over all days is the answer.

### Complexity

- Time: O(n) — one pass.
- Space: O(1) — two integers.

### Trade-offs

Equivalent to the running minimum, with the same cost; its value is the connection it makes, which turns several stock problems into maximum-subarray problems. The running minimum is the more direct explanation in an interview.

### Pitfalls and edge cases

- Clamping at 0 encodes "start a new trade or do not trade"; without it, a long fall at the start would poison every later sum.
- Loop from the second day; the first day has no change.

### Language notes

- Python: index-based iteration avoids building a list of differences or a shifted copy of `prices`.
- TypeScript, Java and Kotlin: the same two-variable loop.
