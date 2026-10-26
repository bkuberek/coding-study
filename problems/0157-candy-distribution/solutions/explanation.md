# Candy Distribution: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| relaxation | brute | O(n^2) | O(n) | a correctness baseline that follows the rules literally |
| two-pass | optimal | O(n) | O(n) | default answer |
| slope-counting | optimal | O(n) | O(1) | the follow-up asks for constant memory |

Each child's minimum is forced by the runs around it: a child at the end of a rising run of length `a` from the left needs at least `a + 1` candies, and a child at the top of a falling run of length `b` to the right needs at least `b + 1`. The answer gives each child exactly the larger of the two requirements, and the approaches differ in how they compute it.

## Approach: relaxation (Repeat passes that fix violated neighbors until nothing changes)

### Intuition

Start everyone at one candy. Whenever a child outscores a neighbor but does not have more candies, raise that child to one more than the neighbor. Keep sweeping until a full pass changes nothing. Every raise is forced, so the final state is the minimum.

### Algorithm

1. Give every child 1 candy.
2. Repeat: for each child, if it outscores its left neighbor without having more candies, set it to the neighbor's count plus 1; do the same for the right neighbor. Stop after a pass with no change.
3. Return the sum.

### Correctness

Invariant: every count is at most the child's value in the optimal distribution. It holds at the start (the optimum gives everyone at least 1), and a raise to `neighbor + 1` keeps it, because the optimum also gives this child more than the neighbor, whose optimal count is at least its current count. The loop ends because counts only grow and are bounded by the optimum. When it ends, no rule is violated, so the counts form a valid distribution that is at most the optimum everywhere: it is the optimum.

### Complexity

- Time: O(n^2) — a strictly falling line moves the fix one child per pass, so it needs about `n` passes of `n` steps.
- Space: O(n) — the candy counts.

### Trade-offs

The most direct reading of the rules and easy to argue, so it is the oracle; the number of passes is what the next approach eliminates.

### Pitfalls and edge cases

- Equal neighbors impose nothing; using `>=` would force a chain of equal scores to keep increasing.
- Stop only after a full pass without changes; one change can create a violation further to the left.

### Language notes

- Python and TypeScript: a `changed` flag drives the outer loop.
- Java and Kotlin: `Arrays.stream(candies).sum()` and `IntArray.sum()` total the result; at most about 2 * 10^8 candies, inside 32-bit range.

## Approach: two-pass (Satisfy left neighbors then right neighbors)

### Intuition

Split the rules by direction. One left-to-right pass gives the fewest candies that respect every left neighbor: each child gets one more than its left neighbor when it outscores it, else 1. One right-to-left pass computes the same for right neighbors. Each child must satisfy both, so it needs the larger of the two values, and taking the maximum on the second pass gives exactly that.

### Algorithm

1. Give every child 1 candy.
2. For `i` from 1 to `n - 1`: if `ratings[i] > ratings[i - 1]`, set `candies[i] = candies[i - 1] + 1`.
3. For `i` from `n - 2` down to 0: if `ratings[i] > ratings[i + 1]`, set `candies[i] = max(candies[i], candies[i + 1] + 1)`.
4. Return the sum.

### Correctness

After step 2, `candies[i] = left[i]`, the length of the rising run ending at `i` plus 1, which is a lower bound for child `i` in any valid distribution. Step 3 computes `right[i]` the same way and keeps `max(left[i], right[i])`, also a lower bound. The result is valid: for a pair where `i` outscores `i + 1`, step 3 sets `candies[i] > candies[i + 1]` and later steps only touch smaller indexes; for a pair where `i + 1` outscores `i`, `candies[i + 1] >= left[i + 1] = left[i] + 1`, and `candies[i] = left[i]` because `right[i] = 1` when `i` does not outscore its right neighbor. Greedy exchange view: no child can get fewer than its own lower bound, and giving exactly the bound everywhere is valid, so no distribution uses fewer candies.

### Complexity

- Time: O(n) — two linear passes and a sum.
- Space: O(n) — the candy array.

### Trade-offs

The standard answer: two short loops and a clean argument. Its linear memory is the only thing the slope-counting version improves.

### Pitfalls and edge cases

- In the second pass, take the maximum; overwriting with `candies[i + 1] + 1` breaks the left-neighbor rule at peaks where the rising side is longer.
- A single child gets 1 candy; both loops do nothing.

### Language notes

- Python: two `range` loops, one of them reversed with step -1.
- TypeScript: `reduce` sums the counts.
- Kotlin: `for (i in n - 2 downTo 0)` is empty when `n` is 1.

## Approach: slope-counting (One pass over rising and falling runs)

### Intuition

Read the line as rising runs, falling runs and ties. On a rising run, the `k`-th child after a valley gets `k + 1` candies, so each step adds `up + 1`. On a falling run, count from the bottom instead: when the run grows to length `d`, its `d` children below the peak need `1, 2, ..., d`, so the step costs `d` more candies (the new bottom child gets 1 and each of the others moves up by one). The peak was counted with `peak + 1` candies on the way up; it needs one more only when `d` exceeds `peak`, because only then does its right requirement `d + 1` beat its left requirement. A tie resets everything.

### Algorithm

1. Start with `total = 1` (the first child) and `up = down = peak = 0`.
2. For each next child: if the score rises, `up += 1`, `peak = up`, `down = 0`, and add `up + 1`. If it ties, reset `up`, `down` and `peak` to 0 and add 1. If it falls, `up = 0`, `down += 1`, and add `down`, plus 1 more when `down > peak`.
3. Return `total`.

### Correctness

The sum equals the two-pass result. On a rising run, the added amounts are `2, 3, ...`, the left requirements. On a falling run of current length `d`, its children need `1, 2, ..., d` counting from the bottom, plus the peak's own requirement `max(peak + 1, d + 1)`; each step down shifts every child of the run up by one, which costs `d` (the new bottom child gets 1 and every other child gains 1), and the peak gains one more only while `d` exceeds `peak`, which is when `d + 1` overtakes `peak + 1`. A tie makes both neighbors independent, so starting a fresh segment is right.

### Complexity

- Time: O(n) — one pass with constant work per child.
- Space: O(1) — four integers.

### Trade-offs

Constant memory and a single pass, at the cost of a subtle invariant that is easy to get off by one. Present the two-pass solution first and offer this one as the optimization.

### Pitfalls and edge cases

- Reset `peak` on ties: after a plateau the next falling run starts from a peak of height 1.
- Compare `down > peak`, not `>=`: when the two slopes have equal length, the peak's left requirement already covers its right one.

### Language notes

- Kotlin: a `when` without a subject replaces the `if` chain; `total += down + if (down > peak) 1 else 0` uses `if` as an expression.
- All four languages keep the same four counters.
