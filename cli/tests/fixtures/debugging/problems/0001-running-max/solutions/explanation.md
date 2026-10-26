# Running Maximum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| single-pass | optimal | O(n) | O(n) | default answer |

## Approach: single-pass (Single pass)

### Intuition

The buggy version starts the maximum at 0, which beats every negative value. Start from the first element instead.

### Algorithm

1. Set the maximum to `nums[0]`.
2. For each value, keep the larger of it and the maximum, and append the maximum.

### Correctness

After reading position `i` the maximum equals the largest of `nums[0..i]`, by induction on `i`.

### Complexity

- Time: O(n) — one pass.
- Space: O(n) — the output array.

### Trade-offs

Any sentinel smaller than every input works too, but the first element needs no knowledge of the value range.

### Pitfalls and edge cases

Arbitrary sentinels such as 0 or -1 fail on negative input; in Java and Kotlin `Integer.MIN_VALUE` is safe only because no arithmetic is done on it.

### Language notes

The fix is the same in every language.
