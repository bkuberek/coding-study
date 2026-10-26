# Car Pooling: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| load-at-pickups | brute | O(n^2) | O(1) | a handful of trips, or as a correctness oracle |
| sorted-events | optimal | O(n log n) | O(n) | locations are large or sparse (no bound to index an array by) |
| difference-array | optimal | O(n + L) | O(L) | default answer when locations are small integers |

`n` is the number of trips and `L` the largest drop-off location. The generated inputs use locations up to `4n`, so `L` grows with `n`. All three approaches rely on one observation: the load changes only at pickups and drop-offs, and it can only rise at a pickup.

## Approach: load-at-pickups (Count the riders at every pickup point)

### Intuition

The busiest moment of the run starts at some pickup: between two consecutive events the load is constant, and only a pickup increases it. So it is enough to measure the load right after each pickup location and compare the largest one with the capacity.

### Algorithm

1. For every trip, take its pickup location `p`.
2. Add up the passengers of every trip with `start <= p < end` (on board just after `p`, since riders ending at `p` have left).
3. Keep the largest of those loads, and return whether it is at most `capacity`.

### Correctness

Let `x` be a location where the load is at its maximum, chosen as far left as possible. The load just left of `x` is smaller (or `x` is the first location), so some trip starts at `x`, and `x` is one of the measured pickup points. The load at a pickup `p` is exactly the passengers of trips whose half-open interval `[start, end)` contains `p`, which step 2 adds. So the largest measured load is the true maximum.

### Complexity

- Time: O(n^2) — n pickup points, each checked against n trips.
- Space: O(1) — a running sum and the largest load.

### Trade-offs

No sorting and no extra memory, and the half-open interval test makes the drop-off-before-pickup rule explicit. It repeats almost the same sum for nearby pickups; sorting the events lets one running total serve all of them.

### Pitfalls and edge cases

- Use `start <= p < end`, not `<= end`: riders leaving at `p` must not count against riders boarding at `p`.
- Measuring at drop-off locations instead of pickups misses the peak: right after a drop-off, the load has just gone down.

## Approach: sorted-events (Sweep pickups and drop-offs in location order)

### Intuition

Replace each trip by two events, `+passengers` at its start and `-passengers` at its end. Walking the events in location order while keeping a running total reproduces the load along the road. Ties at one location must apply drop-offs first.

### Algorithm

1. Build `2n` events `(location, change)`.
2. Sort them by location, then by change, so negative changes (drop-offs) come first at a shared location.
3. Add the changes in order; if the running load ever exceeds `capacity`, return `false`.
4. Return `true`.

### Correctness

After processing every event at locations up to and including `x` (drop-offs first), the running total equals the number of riders on board just after `x`: each trip has contributed `+passengers` once it started and `-passengers` once it ended. Within one location, applying the drop-offs first means the intermediate totals are never larger than the true loads before and after `x`, so no false overflow is reported, while every true load is reached after some pickup event and checked.

### Complexity

- Time: O(n log n) — sorting `2n` events dominates the linear sweep.
- Space: O(n) — the event list.

### Trade-offs

Works for any locations, however large or sparse, which is why it is the general technique (it is the same sweep as counting meeting rooms). When locations are small integers, the difference array avoids the sort.

### Pitfalls and edge cases

- The tie-break matters: sorting pickups before drop-offs at the same location reports overflows that never happen (Example 2).
- Sorting by location only, with an unstable sort, leaves the tie order to chance.

### Language notes

- Python: tuples `(location, change)` already sort by location, then change, so `events.sort()` applies the tie-break for free.
- TypeScript: the comparator `a[0] - b[0] || a[1] - b[1]` falls through to the change when locations are equal.
- Java: `Comparator.<int[]>comparingInt(e -> e[0]).thenComparingInt(e -> e[1])` on an `int[][]`; the explicit type witness lets the chained comparator infer `int[]`.
- Kotlin: `compareBy<IntArray>({ it[0] }, { it[1] })` builds the same two-key comparator; `for ((passengers, start, end) in trips)` destructures each `IntArray`.

## Approach: difference-array (Difference array over locations)

### Intuition

When locations are small integers, the events can be bucketed directly: `change[x]` collects every `+passengers` and `-passengers` at location `x`. The load just after `x` is then the prefix sum `change[0] + ... + change[x]`, and summing within a bucket handles ties automatically.

### Algorithm

1. Find `L`, the largest drop-off location, and create `change` with `L + 1` zeros.
2. For every trip: `change[start] += passengers` and `change[end] -= passengers`.
3. Walk the array with a running sum; if it exceeds `capacity`, return `false`.
4. Return `true`.

### Correctness

The prefix sum at `x` counts `+passengers` for every trip with `start <= x` and `-passengers` for every trip with `end <= x`, which leaves exactly the trips with `start <= x < end`: the riders on board just after location `x`. Every location's load is checked, and the load between two integer locations equals the load at the left one.

### Complexity

- Time: O(n + L) — one pass over the trips and one over the locations.
- Space: O(L) — the change array.

### Trade-offs

The fastest approach here, and the usual interview answer when the location bound is small (it is a one-dimensional "range update, point query" trick). With huge or sparse locations, `L` dominates and the sorted sweep wins; with many queries over a changing set of trips, a Fenwick tree generalizes it.

### Pitfalls and edge cases

- Size the array by the largest drop-off, not the largest pickup: `change[end]` must exist.
- The drop-off is subtracted at `end`, not at `end + 1`, because riders leave at `end`.
- A fixed array of `10^5 + 1` entries is also correct, but then every call pays for the full road; sizing it by the input keeps small inputs cheap.

### Language notes

- Python: `max(accumulate(change)) <= capacity` computes every load in C; it scans the whole array instead of stopping early, which costs at most O(L) extra.
- TypeScript: an `Int32Array` is zero-filled, compact and fast to scan; loads stay below 10^6.
- Java and Kotlin: `new int[L + 1]` and `IntArray(L + 1)` are zero-initialized; Kotlin's `maxOf { it[2] }` finds `L` in one expression.
