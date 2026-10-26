# Jump Game: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| mark-reachable | brute | O(n^2) | O(n) | first idea; a correctness baseline |
| farthest-reach | optimal | O(n) | O(1) | default answer |
| leftmost-good | optimal | O(n) | O(1) | you prefer reasoning backwards from the goal |

The brute force is a dynamic program over indexes: an index is reachable if some reachable index can jump to it. The greedy insight that collapses it: the reachable indexes always form a prefix of the array, because a jump of length up to `k` can also stop short. A prefix is described by one number, its right end.

## Approach: mark-reachable (Mark every index a reachable index can jump to)

### Intuition

Process indexes from left to right. Index 0 is reachable. Whenever the current index is reachable, every index it can jump to becomes reachable too. Every jump goes forward, so when the loop reaches an index, all the jumps that can land on it have already been processed.

### Algorithm

1. Mark index 0 reachable.
2. For each index `i` from left to right: skip it if it is not reachable; return `true` if it is the last index; otherwise mark `i + 1` to `min(last, i + nums[i])` reachable.
3. Return whether the last index is marked.

### Correctness

Invariant: when the loop reaches index `i`, it is marked exactly when it is reachable. A reachable `i > 0` is reached by a last jump from some reachable `j < i` with `j + nums[j] >= i`; `j` was processed earlier and marked `i`. Conversely, only targets of reachable indexes are ever marked.

### Complexity

- Time: O(n^2) — each reachable index marks up to `n` targets; inputs with long jumps that all stop before a 0 reach that bound.
- Space: O(n) — the reachability array.

### Trade-offs

A direct translation of the definition, so it is the oracle. Marking the same targets again and again is the waste the greedy removes.

### Pitfalls and edge cases

- Cap the targets at the last index; `i + nums[i]` can be far past the end.
- A single-element array is already at the last index: the answer is `true` even if its value is 0.

### Language notes

- All four languages use a boolean array; values up to 10^5 plus an index stay far inside 32-bit range.

## Approach: farthest-reach (Track the farthest reachable index)

### Intuition

Since the reachable indexes form a prefix `0..farthest`, it is enough to track `farthest`. Walking left to right, every index up to `farthest` is reachable and may extend it to `i + nums[i]`. Reaching an index beyond `farthest` means the walk is stuck.

### Algorithm

1. Set `farthest = 0`.
2. For each index `i`: if `i > farthest`, return `false`; otherwise set `farthest = max(farthest, i + nums[i])`.
3. Return `true`.

### Correctness

Invariant: before index `i`, the reachable indexes among `0..i - 1` are exactly a prefix, and `farthest` is the farthest index any of them can jump to. If `i <= farthest`, some reachable index can land on `i` (jumps may stop short), so `i` is reachable and its jump extends the prefix. If `i > farthest`, no reachable index can land on `i`, and no index after `i` is reachable either, since that would need a jump from before `i` that passes over `i`. Greedy argument: there is no need to choose which jump to take, because reaching farther never removes options; the farthest reach dominates every other choice.

### Complexity

- Time: O(n) — one pass, constant work per index.
- Space: O(1) — one integer.

### Trade-offs

The expected answer: shortest code and a clean exchange argument. It also generalizes to the "minimum number of jumps" variant by counting how many times the frontier is extended.

### Pitfalls and edge cases

- Check `i > farthest` before updating; otherwise a 0 at `i` beyond the frontier would be skipped over silently.
- Returning `true` as soon as `farthest >= last` is a valid early exit.

### Language notes

- All four languages use the same loop; `i + nums[i]` is at most about 1.1 * 10^5, no overflow concern.

## Approach: leftmost-good (Move the goal backwards)

### Intuition

Work from the end. The last index is a goal. Walking leftwards, any index whose jump reaches the current goal can get to the end (through the goal), so it becomes the new, closer goal. The answer is whether the goal moves all the way to index 0.

### Algorithm

1. Set `goal` to the last index.
2. For `i` from the second-to-last index down to 0: if `i + nums[i] >= goal`, set `goal = i`.
3. Return `goal == 0`.

### Correctness

Invariant: after processing index `i`, `goal` is the leftmost index in `i..last` from which the last index is reachable. If `i` can jump to `goal` or beyond, it can stop exactly at `goal` (jumps may stop short), so `i` reaches the end and is the new leftmost such index. If it cannot reach `goal`, it cannot reach any good index to the right either, because every good index to the right is at or after `goal`, and an index that can reach a farther one could also stop at `goal`. Hence `i` is not good. At the end, index 0 is good exactly when `goal == 0`.

### Complexity

- Time: O(n) — one backward pass.
- Space: O(1) — one integer.

### Trade-offs

Same cost as the forward greedy; some people find "move the goal" easier to prove than "extend the frontier". It always scans the whole array, while the forward version can stop early.

### Pitfalls and edge cases

- Start from the second-to-last index; the last index is the initial goal.
- The comparison is `>=`: landing exactly on the goal is enough.

### Language notes

- Kotlin: `for (i in nums.size - 2 downTo 0)` is empty for a single-element array, which correctly returns `true`.
