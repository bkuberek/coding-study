# Gas Station: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | first idea; a correctness baseline |
| reset-on-deficit | optimal | O(n) | O(1) | default answer |
| lowest-prefix | optimal | O(n) | O(1) | you prefer one argument about the running balance |

Write `surplus[i] = gas[i] - cost[i]`, the net fuel change of the leg that leaves station `i`. A start works when every partial sum of surpluses along the circle, beginning at that start, stays non-negative. Two facts carry both linear solutions: if the total surplus is negative no start works (the trip as a whole loses fuel), and if it is non-negative some start does.

## Approach: brute-force (Simulate the trip from every station)

### Intuition

Try every station as the start, drive around the circle adding each leg's surplus to the tank, and stop at the first leg where the tank goes negative. The first start that survives all `n` legs is the answer.

### Algorithm

1. For each `start` from 0 to `n - 1`: set `fuel = 0`; for `step` from 0 to `n - 1`, add the surplus of station `(start + step) mod n`; stop if `fuel < 0`.
2. If all `n` legs were driven, return `start`.
3. Return -1.

### Correctness

The simulation follows the rules exactly: fill up at the current station, then pay for the leg to the next one, and fail if the tank would go below zero. Each start is tested on its own, so the first start that survives is a valid answer, and by uniqueness it is the answer.

### Complexity

- Time: O(n^2) — up to `n` starts, each simulating up to `n` legs; inputs where every wrong start survives until the last leg reach that bound.
- Space: O(1) — the tank and two counters.

### Trade-offs

Direct and easy to trust, so it is the oracle. Each failed simulation throws away everything it learned; the greedy approaches keep it.

### Pitfalls and edge cases

- Wrap around with `mod n`; a trip from station `start` continues through station `n - 1` to station 0.
- Fill up before paying for the leg: a station with `gas[i] >= cost[i]` is a valid single-station circuit.

### Language notes

- Python: the `for ... else` clause runs only when the inner loop did not break, which marks a successful trip.
- TypeScript, Java and Kotlin: a `step` counter that reaches `n` marks success.

## Approach: reset-on-deficit (One pass that restarts after every empty tank)

### Intuition

Suppose a trip from station `a` first runs dry on the leg leaving station `b`. Then no station between `a` and `b` can be a valid start either: when the trip from `a` arrived at any such station `c`, it carried a non-negative amount of fuel, so starting at `c` with an empty tank is never better, and it would also run dry by `b`. So when the tank goes negative, skip directly to `b + 1` and start counting again. One pass over the stations then leaves a single candidate, and the total surplus decides whether it works.

### Algorithm

1. Set `total = 0`, `fuel = 0`, `start = 0`.
2. For each station: add its surplus to `total` and to `fuel`; if `fuel < 0`, set `start` to the next station and `fuel = 0`.
3. Return `start` if `total >= 0`, else -1.

### Correctness

Exchange argument for the skip: compared with starting at `a`, starting at a station `c` in `(a, b]` drops the prefix `a..c - 1`, whose sum is non-negative (the tank had not run dry before `b`), so every partial sum from `c` up to `b` is at most the corresponding one from `a`, and the one ending at `b` is negative. Hence every skipped station is invalid. If `total < 0`, no start can work and -1 is right. If `total >= 0`, some start is valid (the lowest-prefix argument below constructs one), and every station before the final `start` has been ruled out, so the valid start is the final `start`; in particular `start` is then less than `n`.

### Complexity

- Time: O(n) — one pass, constant work per station.
- Space: O(1) — three integers.

### Trade-offs

The expected interview answer: one pass, constant memory, and a crisp skipping argument. It returns `start` even for `start == n` if the last leg runs dry, but then `total` is negative, so -1 is returned instead.

### Pitfalls and edge cases

- Reset to the next station, not to the station after the original start: every station up to the failing one is ruled out.
- Check `total`, not the final `fuel`; `fuel` only covers the stations after the last reset.

### Language notes

- All four languages use the same three-variable loop; totals stay below 10^9, inside 32-bit range.

## Approach: lowest-prefix (Start right after the lowest running balance)

### Intuition

Drive from station 0 with a magic tank that may go negative, and record the running balance after each leg. Starting the real trip at station `s` shifts every running balance down by the balance just before `s`. The shift that lifts the whole curve to non-negative values is the one that starts right after the point where the balance is lowest. If the circle as a whole loses fuel, the curve ends below where it began and no shift helps.

### Algorithm

1. Set `balance = 0`, `lowest = 0`, `start = 0`.
2. For each station: add its surplus to `balance`; if `balance < lowest`, set `lowest = balance` and `start` to the next station.
3. Return -1 if `balance < 0`; otherwise return `start mod n`.

### Correctness

Let `B(k)` be the balance after the first `k` legs from station 0, with `B(0) = 0` and `B(n) = total >= 0`. Starting at `s`, the fuel after reaching a point `k > s` is `B(k) - B(s)`, and after wrapping to a point `k <= s` it is `total + B(k) - B(s)`. Choosing `s` with `B(s)` minimal over `0..n - 1` makes the first kind non-negative, and the second as well because `total >= 0`. The loop records the earliest position of the minimum, so it returns such a start; when `total >= 0` the final balance `B(n)` is at least `B(0) = 0`, so it never becomes a new strict minimum and `start` stays below `n`.

### Complexity

- Time: O(n) — one pass.
- Space: O(1) — three integers.

### Trade-offs

Same cost as the reset version and arguably the cleanest proof: the whole problem becomes "where is the minimum of a prefix sum". It is less obvious to invent on the spot, so it makes a good second explanation.

### Pitfalls and edge cases

- `start` can reach `n` only when the last leg sets a new minimum, which means the total is negative and the answer is -1; the final `% n` is a harmless safeguard.
- Use a strict `<` so a tie keeps the earlier position; with a unique answer the minimum before the true start is strict anyway.

### Language notes

- All four languages use the same loop; balances stay within plus or minus 10^9, inside 32-bit range.
