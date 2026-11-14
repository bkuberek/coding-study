# Car Fleet: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | few cars, or as a correctness oracle |
| sort-and-stack | optimal | O(n log n) | O(n) | default answer |

Everything follows from one fact. Let `t(i) = (target - position[i]) / speed[i]` be the hour car `i` would arrive on an empty road. A car is held back exactly when some car ahead of it would arrive no earlier, so a car starts its own fleet (it is a fleet's front car) if and only if it arrives strictly later than every car ahead of it. The number of fleets is the number of such front cars.

## Approach: brute-force (Compare each car with the slowest car ahead of it)

### Intuition

For each car, find the car ahead of it with the latest arrival time. If our car would arrive strictly later still, nobody ahead can hold it back and it leads a fleet; otherwise it catches up with that car (or with the fleet that car is stuck in) before or at the destination.

### Algorithm

1. Set `fleets = 0`.
2. For each car `i`:
   1. Scan every car `j` with `position[j] > position[i]` and keep the one with the latest arrival time.
   2. If there is none, or `t(i)` is strictly greater than its arrival time, add 1 to `fleets`.
3. Return `fleets`.

Arrival times are compared without division: `t(a) > t(b)` exactly when `(target - position[a]) * speed[b] > (target - position[b]) * speed[a]`.

### Correctness

The fleet directly ahead of car `i` arrives at the latest arrival time among all cars ahead of `i`: a fleet moves at the pace of its slowest member, and every car ahead is either in that fleet or in a fleet further ahead, which arrives no later. Car `i` catches up with it before or at the destination exactly when `t(i)` is at most that time. So the cars counted are exactly the fronts of the fleets, one per fleet.

### Complexity

- Time: O(n^2) — every car scans all n cars.
- Space: O(1) — one index for the slowest car ahead.

### Trade-offs

No sorting and only integer arithmetic, so it is easy to trust and serves as the oracle. At 5,000 cars it already makes 25 million comparisons; sorting reduces the work to one pass.

### Pitfalls and edge cases

- Compare with the latest arrival among all cars ahead, not just the nearest car ahead: a car can be held back by a slow car several positions further up.
- A tie (arrival exactly at the same hour) means the cars merge, so the front-car test must be strict.
- The products are at most 10^6 * 1000 = 10^9 here, which fits a 32-bit integer; with larger limits, cross-multiply in 64 bits.

### Language notes

- All four references are two nested loops; Python precomputes the distances once, and Java puts the cross-multiplication into a static helper, while TypeScript and Kotlin use a local function.
- Go: `int` is 64 bits, so the cross products (at most 10^6 times 10^3) never overflow; a closure `arrivesLater` names the comparison.
- Rust: the products also fit in `i32` (at most 10^9), but cstudy builds Rust with overflow checks, so the reference widens the distances to `i64` and leaves a wide margin. The slowest car ahead is an `Option<usize>` and `match` with a guard decides whether the next car ahead replaces it.

## Approach: sort-and-stack (Sort by position, then stack the fleet arrival times)

### Intuition

Sort the cars by position and walk from the car farthest back toward the destination. The stack holds the fleets formed behind the current car, farthest back at the bottom; each fleet arrives strictly later than the fleet in front of it, or the two would have merged, so the times strictly decrease toward the top. A new car closer to the destination is caught by every fleet on top of the stack that would arrive no later than it does: pop them all, then push the new car's time as the time of the merged fleet.

### Algorithm

1. Sort the cars by position, ascending.
2. For each car in that order, compute `arrival = (target - position) / speed`.
   1. While the stack is not empty and its top time is at most `arrival`, pop it.
   2. Push `arrival`.
3. Return the size of the stack.

### Correctness

Invariant: after processing the k cars farthest back, the stack holds one entry per fleet those k cars would form among themselves, with that fleet's arrival time, ordered by position and strictly decreasing in time from bottom to top. A new car is ahead of all of them. The fleets that catch up with it are exactly those with arrival time at most its own; because times decrease toward the top, they are a run at the top of the stack, which the loop pops. They now move at the new car's pace, so the merged fleet arrives at `arrival`, which is pushed; the entry below it is strictly later, so the order holds. Cars further ahead only slow down fleets as a whole and never split them, so the final stack counts the fleets.

### Complexity

- Time: O(n log n) — the sort dominates; the stack pass pushes and pops each car at most once.
- Space: O(n) — the sorted order and the stack.

### Trade-offs

This is the standard answer and shows the monotonic stack clearly. Walking from the front car backwards with a single "current fleet time" variable is equivalent and needs no stack; the stack version generalizes to questions such as "which fleet does each car end up in". Because positions are below `target`, a counting sort (an array indexed by mile) can replace the comparison sort when `target` is small, for O(n + target) time.

### Pitfalls and edge cases

- Sort cars as pairs (or sort indexes): sorting `position` alone loses which speed belongs to which car.
- Pop on `<=`, not `<`: a fleet arriving at the same hour merges at the destination.
- Floating-point arrival times are safe here: two different fractions with denominators up to 1000 differ by at least 10^-6, far more than the rounding error of a double near 10^6, and equal fractions round to the same double. Cross-multiplying, as in the brute force, avoids the question entirely.

### Language notes

- Python: `sorted(zip(position, speed))` sorts the cars as tuples by position; a list is the stack.
- TypeScript: sorts an array of indexes with a numeric comparator; the default `sort()` would compare the numbers as strings.
- Java: an `Integer[]` of indexes sorted with `Comparator.comparingInt`, and a primitive `double[]` with a size counter as the stack.
- Kotlin: `position.indices.sortedBy { position[it] }` gives the indexes in position order; `ArrayDeque<Double>` is the stack.
- Go: the reference sorts a slice of car indexes with `slices.SortFunc` and `cmp.Compare` instead of sorting two slices in step, which leaves the inputs untouched. Arrival times are `float64`; two equal rationals produce the same quotient, so the `<=` comparison is exact here.
- Rust: `sort_unstable_by_key(|&car| position[car])` orders the index vector; the positions are distinct, so stability does not matter. `f64` is not `Ord`, which rules out `sort()` and `BinaryHeap` on arrival times, but the stack only needs `<=`. `f64::from` widens the `i32` values exactly.
