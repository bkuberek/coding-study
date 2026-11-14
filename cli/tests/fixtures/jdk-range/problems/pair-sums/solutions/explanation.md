# Pair Sums: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| gatherer | optimal | O(n) | O(n) | default answer |

## Approach: gatherer (Sliding windows of two)

### Intuition

Every sum uses a value and its right neighbour: a window of two that slides one step at a time.

### Algorithm

1. Box the values into a stream.
2. Gather sliding windows of two.
3. Keep the windows that hold two values: a stream shorter than the window yields one short window.
4. Add the two values of each window.

### Correctness

A window of two starts at every position but the last, so each pair of neighbours is added once.

### Complexity

- Time: O(n) — each value is in at most two windows.
- Space: O(n) — the boxed values and the result.

### Trade-offs

Needs the stream gatherers of JDK 24; a plain loop needs no gatherer.

### Pitfalls and edge cases

An array of fewer than two values has no window.

### Language notes

The reference uses `Stream.gather` and `Gatherers.windowSliding`, final in JDK 24: a problem that uses them declares `jdk: {min: 24}`.
