# Sum of Subarray Minimums: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | small arrays, or as a correctness oracle |
| contribution | optimal | O(n) | O(n) | default answer; generalizes to maximums and other aggregates |
| stack-dp | optimal | O(n) | O(n) | when you think of it as "answers per end position" |

Both linear approaches rest on the previous smaller element of each position, found with a stack whose values strictly increase from bottom to top. The contribution approach asks "how many subarrays is `arr[i]` the minimum of?"; the stack DP asks "what do the subarrays ending at `i` add up to?".

## Approach: brute-force (Extend every start with a running minimum)

### Intuition

Fix the start of a subarray and move its end to the right one step at a time. The minimum of the growing subarray is the old minimum or the new element, whichever is smaller, so each subarray costs O(1) and nothing is recomputed from scratch.

### Algorithm

1. Set `total = 0`.
2. For each start `i`, set `minimum = arr[i]`; for each end `j` from `i` to `n - 1`, set `minimum = min(minimum, arr[j])` and add it to `total`.
3. Return `total` modulo `10^9 + 7`.

### Correctness

For a fixed start, the running minimum after step `j` is the minimum of `arr[i..j]` by induction on `j`. Every pair `i <= j` is visited exactly once, so `total` is the sum over all subarrays.

### Complexity

- Time: O(n^2) — one constant-time step per subarray, and there are n (n + 1) / 2 of them.
- Space: O(1) — a running minimum and the total.

### Trade-offs

Simple and obviously right, so it is the oracle. It does no redundant work per subarray; the problem is the number of subarrays itself, which the linear approaches avoid by grouping subarrays that share a minimum.

### Pitfalls and edge cases

- Recomputing the minimum of each subarray from scratch would cost O(n^3).
- The raw sum reaches about 1.35 * 10^13 at the limits, beyond 32 bits; reduce modulo `10^9 + 7` with a 64-bit total.

### Language notes

- Python: `accumulate(arr[start:], min)` produces the running minimums for one start in C, and `sum` adds them; Python integers never overflow, so one reduction at the end suffices.
- TypeScript: one start adds at most 9 * 10^8, so reducing once per start keeps every value exact in a double.
- Java and Kotlin: the total is a `long`, reduced once per start.
- Go: `int` is 64 bits, so the running total cannot overflow; the reference still reduces it once per start, as the Java and Kotlin versions do, and uses the built-in `min` (Go 1.21 and newer).
- Rust: the total is an `i64`. With the per-start reduction an `i32` would just fit (below 2 * 10^9) but leave almost no margin, and cstudy builds Rust with overflow checks, so a slip would panic instead of wrapping. The final `% MOD` is below 2^31, so `as i32` is exact.

## Approach: contribution (Count the subarrays where each element is the minimum)

### Intuition

Instead of visiting subarrays, give each element the credit for the subarrays it is the minimum of. If the nearest strictly smaller element on the left is at `p` and the nearest smaller-or-equal element on the right is at `q`, then `arr[i]` is the minimum of exactly the subarrays that start in `(p, i]` and end in `[i, q)`: `left = i - p` starts times `right = q - i` ends. Its contribution is `arr[i] * left * right`.

A single stack pass finds both boundaries: keep indexes with strictly increasing values. When a new value is at most the value on top, the top's right boundary has arrived; the index just below it in the stack is its left boundary. Settle its contribution as it is popped.

### Algorithm

1. Walk `index` from 0 to `n`, using `value = arr[index]`, or 0 for the extra step `index = n` (0 is below every element, so it pops everything left).
2. While the stack is not empty and `arr[top] >= value`:
   1. Pop `middle`; let `below` be the new top, or -1 if the stack is empty.
   2. Add `arr[middle] * (middle - below) * (index - middle)` to the total.
3. Push `index`.
4. Return the total modulo `10^9 + 7`.

### Correctness

Stack invariant: values strictly increase from bottom to top, and the element below each index is its previous strictly smaller element. When `middle` is popped by `index`, every element between `middle` and `index` was popped earlier by something no larger, so all of them are at least `arr[middle]`, and `arr[index] <= arr[middle]`: `index` is its next smaller-or-equal element. Hence `arr[middle]` is the minimum of exactly `left * right` subarrays.

Ties are broken asymmetrically on purpose. A subarray whose minimum value occurs at several positions is credited only to its rightmost copy: that copy's left boundary passes over equal values (strictly smaller stops it), while every other copy's right boundary stops at the next equal value. So every subarray is counted exactly once.

### Complexity

- Time: O(n) — each index is pushed once and popped once.
- Space: O(n) — the stack.

### Trade-offs

The standard answer; the same counting gives the sum of subarray maximums, and their difference gives the sum of subarray ranges. The tie rule is the part interviewers probe. A two-pass variant computes the left and right boundaries in separate arrays first, which is easier to debug at the cost of two extra arrays.

### Pitfalls and edge cases

- Using "smaller or equal" on both sides undercounts repeated minimums; using "strictly smaller" on both sides counts them twice. Example 2 and the `[2, 4, 2, 4]` case catch both mistakes.
- `arr[i] * left * right` reaches about 6.75 * 10^12: compute it in 64 bits (Java `long`, Kotlin `Long`).
- The sentinel 0 works because every value is at least 1.

### Language notes

- Python: a list as the stack; arbitrary-precision integers, so one reduction at the end.
- TypeScript: the product stays below 2^53, so it is exact as a double; the total is reduced on every step.
- Java: a primitive `int[]` stack with a size counter; `left` and `right` are declared `long` so the product is computed in 64 bits.
- Kotlin: `ArrayDeque<Int>` with `lastOrNull() ?: -1` for the missing left boundary; `toLong()` before multiplying.
- Go: `arr[middle] * left * right` is at most 2.7 * 10^13, far inside a 64-bit `int`, so the total is reduced once at the end.
- Rust: the reference widens to `i64` before multiplying (`i64::from(arr[middle]) * left * right`), because the product exceeds `i32`. `arr.get(index).copied().unwrap_or(0)` supplies the sentinel value 0 without extending the vector, and the missing left boundary is `-1` from `stack.last().map_or(-1, ..)`.

## Approach: stack-dp (Sum of minimums ending at each index from the previous smaller element)

### Intuition

Let `ending[i]` be the sum of the minimums of the subarrays that end at `i`. If `p` is the previous strictly smaller element, the subarrays ending at `i` that start after `p` all have minimum `arr[i]`, which gives `arr[i] * (i - p)`. The ones that start at or before `p` contain `arr[p]`, which is smaller than everything after it up to `i`, so their minimums are exactly those of the subarrays ending at `p`: `ending[p]`. The answer is the sum of all `ending[i]`.

### Algorithm

1. For each `index`, pop the stack while the value on top is at least `arr[index]`.
2. If the stack is empty, `ending[index] = arr[index] * (index + 1)`; otherwise, with `previous` on top, `ending[index] = ending[previous] + arr[index] * (index - previous)`.
3. Push `index` and add `ending[index]` to the total.
4. Return the total modulo `10^9 + 7`.

### Correctness

The recurrence splits the subarrays ending at `i` by whether they include `p`. Those that do not start in `(p, i]`; every element there is at least `arr[i]` (an element smaller than `arr[i]` would be a closer previous smaller element), so their minimum is `arr[i]`. Those that do include `p` have a minimum at or before `p`, because `arr[p] < arr[i]` and everything between `p` and `i` is at least `arr[i]`; extending a subarray that ends at `p` by those elements does not change its minimum, so these sum to `ending[p]`. With no smaller element on the left, all `i + 1` subarrays have minimum `arr[i]`. The stack yields `p` exactly as in the contribution approach.

### Complexity

- Time: O(n) — one push and at most one pop per index.
- Space: O(n) — the `ending` array and the stack.

### Trade-offs

It reads as a one-dimensional DP that the stack makes linear, and it avoids the tie-breaking argument: only the previous strictly smaller element matters. It needs the extra `ending` array, and it does not generalize as directly to "range" variants as the contribution count does.

### Pitfalls and edge cases

- Either tie rule works here: popping on `>=` makes `previous` strictly smaller, popping on `>` lets it be equal, and in both cases every element between `previous` and `i` is at least `arr[i]`. What breaks the recurrence is dropping the `ending[previous]` term, or using an element that is larger than `arr[i]` as `previous`.
- `ending[i]` itself fits in 32 bits (at most 9 * 10^8 here), but the product `arr[i] * (i - previous)` should be computed in 64 bits to be safe, and the total must be reduced.

### Language notes

- Python: `sum(ending) % MOD` at the end; no overflow concerns.
- TypeScript: `ending` values stay below 9 * 10^8; the running total is reduced every step.
- Java: `long[] ending` and a cast `(long) value` before multiplying.
- Kotlin: `LongArray`, with `lastOrNull()` to read the previous smaller index as a nullable `Int`.
- Go: `ending` is a `[]int` of 64-bit values, so `value*(index-previous)` and the running sum need no widening.
- Rust: `ending` is a `Vec<i64>`. A `match` on `stack.last()` separates "there is a previous smaller element" from "there is none", so no `-1` index is needed, and `index - previous` is a safe `usize` subtraction because the stack holds smaller indexes.
