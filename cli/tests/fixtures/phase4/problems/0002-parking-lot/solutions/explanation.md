# Parking Lot: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan | optimal | O(spots) per park, O(1) per leave | O(spots) | default answer at 1000 spots |

## Approach: scan (Occupancy array with a plate map)

### Intuition

The lowest free spot is the first `false` in an occupancy array; a map from plate to spot makes `leave` direct.

### Algorithm

1. Keep `occupied`, one flag per spot, and `spotOf`, a map from plate to spot.
2. `park`: return `-1` for a plate already in `spotOf`; otherwise take the first free spot, or return `-1` when none is free.
3. `leave`: remove the plate from `spotOf` and clear its spot; return whether it was there.
4. `available`: the number of spots minus the size of `spotOf`.

### Correctness

`spotOf` holds exactly the parked cars and `occupied` marks exactly their spots, so the first free flag is the lowest free spot.

### Complexity

- Time: O(spots) per park, O(1) per leave — `park` may scan every spot; map operations are constant on average.
- Space: O(spots) — one flag per spot and at most one map entry per spot.

### Trade-offs

A min-heap of free spots makes `park` O(log spots) at the cost of more code; at 1000 spots the scan is simpler.

### Pitfalls and edge cases

- A car that is already parked must not take a second spot.
- `leave` of an unknown plate returns `false` and changes nothing.

### Language notes

Kotlin's `indexOfFirst` and TypeScript's `indexOf(false)` replace the explicit loop of the Java and Python versions.
