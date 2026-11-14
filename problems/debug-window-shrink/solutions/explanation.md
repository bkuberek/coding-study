# Debug: Window Shrink: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| counted-window | optimal | O(n) | O(k) | default answer: a count map that only holds values inside the window |

## Approach: counted-window (Sliding window with exact counts)

### Intuition

The code decides "all `k` values are distinct" by checking that the count map has exactly `k` keys. That is only true if the map holds exactly the values inside the window. When the window slides, the outgoing value's count is decremented, but a count that reaches `0` stays in the map as a key. From then on the map has more keys than the window has distinct values:

- A window with `k` distinct values plus at least one stale key has more than `k` keys, so it is rejected. That is the "too low" reports: once the first value leaves the window entirely, valid windows are rejected, so only windows near the start are ever counted. With `k = 1`, every step after the first leaves a stale key, so only the first day is ever accepted.
- A window with a repeated value has `k - 1` distinct values. With exactly one stale key it has `k` keys again, so it is accepted. That is the "too high" report (test `h5`: `[2, 3, 3]` is accepted with sum 8).

The fix: when a count drops to zero, remove the key. Then the number of keys equals the number of distinct values in the window at every step.

### Debugging approach

1. **Reproduce with the smallest window.** `k = 1` on `[3, 7, 2]` returns 3, but every element is a valid window. A bug that shows at `k = 1` lives in the sliding bookkeeping, not in a subtle duplicate case.
2. **Instrument the invariant.** At each step, print `counts` next to the actual window `nums[right-k+1..right]`. At step 1 the window is `[7]` while the map is `{3: 0, 7: 1}`. The map has stopped describing the window.
3. **Name the broken invariant.** "`len(counts)` equals the number of distinct values in the window" fails as soon as any count reaches zero.
4. **Check the reverse symptom with the same hypothesis.** The "too high" report needs a window with a duplicate plus exactly one stale key. `[1, 2, 3, 3, 9]` with `k = 3` produces one at window `[2, 3, 3]`. One root cause explains both tickets, which is good evidence.
5. **Compare with a brute force.** Checking every window with a set is O(nk) and obviously correct. Diffing the fast code against it on random small arrays finds the bug in seconds and protects the fix.

### Algorithm

1. Keep `counts` (value to count inside the window), `windowSum` and `best = 0`.
2. For each index `right`:
   1. Add `nums[right]`: increment its count and add it to `windowSum`.
   2. If `right >= k`, the window is too long. Remove `outgoing = nums[right - k]`: decrement its count, **delete the key when the count reaches 0**, and subtract it from `windowSum`.
   3. If the window is full (`right >= k - 1`) and `counts` has exactly `k` keys, set `best = max(best, windowSum)`.
3. Return `best`.

### Correctness

Invariant after step 2: `counts` maps exactly the values inside `nums[right-k+1..right]` (or the prefix, while it is shorter than `k`) to their positive multiplicities, and `windowSum` is their sum. Adding the incoming value and removing the outgoing one keeps both exact, and deleting keys at zero keeps every stored count positive. So the number of keys equals the number of distinct values in the window. A full window has `k` elements, so it has `k` distinct values exactly when the map has `k` keys. Every full window is examined once, so `best` is the maximum over the valid ones, or `0` when there are none.

### Complexity

- Time: O(n) — each element enters and leaves the window once, with O(1) average map operations.
- Space: O(k) — the map holds at most `k` keys, one per value inside the window, now that stale keys are removed.

### Trade-offs

The count map is the general tool and also handles "at most `k` distinct" variants. Because values here are bounded (`1..10^4`), an array of counts plus a separate `distinct` counter, incremented when a count goes from 0 to 1 and decremented when it goes from 1 to 0, avoids hashing entirely. It is faster, but its correctness rests on updating that counter at exactly the right transitions. A brute force over all windows is O(nk): fine as a test oracle, far too slow at n = 10^5.

### Pitfalls and edge cases

- The general trap: when a map's size stands for "distinct items in the window", an entry with count `0` is a lie. Remove it on the way down, or count distinct values separately.
- Python's `collections.Counter` does not save you: `counter[key] -= 1` and `counter.subtract(...)` keep zero and negative counts, and `len()` counts them. (Only the whole-counter operators, such as `counter -= other` or `+counter`, drop non-positive counts.)
- The bug can err in both directions: too low (valid windows rejected) and too high (a duplicate window accepted).
- Shrink before checking. Checking a window of length `k + 1` before removing the outgoing value is a separate off-by-one.

### Prevention

- Write the invariant in a comment next to the map ("keys are exactly the values in the window") and assert it in debug builds: `assert len(counts) == len(set(window))`.
- Keep a brute-force oracle for every sliding-window function and compare on random small inputs, with small value ranges so that values repeat and leave the window.
- Wrap the bookkeeping in a tiny `Multiset` class with `add` and `remove` that deletes at zero, so the rule lives in one place.

### Language notes

- Python: `del counts[key]` (or `counts.pop(key)`) when the count reaches 0. `len(dict)` counts keys, including keys whose value is `0`.
- TypeScript: `Map.size` counts entries; `map.delete(key)` removes one. Setting a value to `0` keeps the entry.
- Java: `computeIfPresent` (like `merge` and `compute`) removes the key when the remapping function returns `null`, which makes "decrement and remove at zero" one call. `put(key, 0)` keeps the entry.
- Kotlin: `counts.remove(key)`; `counts[key] = 0` keeps the entry, and `HashMap.size` counts it. `getValue(key)` throws on a missing key instead of returning `null`, which documents that the outgoing value must be present.
