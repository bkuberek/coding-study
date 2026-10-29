# Fruit Into Baskets: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is small, or as a correctness oracle |
| sliding-window | optimal | O(n) | O(1) | default answer; generalizes to k baskets |
| last-run | optimal | O(n) | O(1) | exactly two baskets; no map needed |

The problem is the longest contiguous subarray with at most two distinct values. The map in `sliding-window` never holds more than three keys, so its space is constant.

## Approach: brute-force (Walk from every starting tree)

### Intuition

Simulate the walk literally: from each start, keep picking while the fruit matches one of at most two types, and stop at the first tree that would need a third basket. The longest walk is the answer.

### Algorithm

1. Set `best = 0`.
2. For each `start`: let `first = fruits[start]` and `second` be empty. Walk `end` from `start` while `fruits[end]` is `first` or `second`, or `second` is still empty (then it becomes `second`). Update `best` with `end - start`.
3. Return `best`.

### Correctness

For a fixed start, the walk stops exactly at the first tree whose type is neither of the two types collected so far, which is the rule of the statement; it is also the longest run from that start with at most two types. Every walk has a start, so the maximum over starts is the answer.

### Complexity

- Time: O(n^2) — each start can walk to the end of the row. The generator builds long two-type stretches, so walks cover about a segment of n/8 to n/4 trees from every start.
- Space: O(1) — two remembered types.

### Trade-offs

It is the statement turned into code, hence the oracle. Consecutive starts share almost all of their walks; the sliding window reuses that work.

### Pitfalls and edge cases

- The first tree's type always fits; a single tree yields 1.
- One type only: the walk covers the whole row.
- Use a sentinel for the empty second basket that cannot be a fruit type (-1 here, since types are at least 0).

### Language notes

- Python: `None` marks the empty basket; comparing an `int` with `None` is simply `False`.
- TypeScript, Java, Kotlin: -1 marks the empty basket.
- Go: the unused basket is the constant `empty = -1`, as in Java and Kotlin, which works because fruit types are never negative.
- Rust: the second basket is an `Option<i32>` instead of a sentinel, so `Some(fruit) != second` and `second.is_some()` read as the Python `is not None` tests. The run length `end - start` is a `usize` and converts to `i32` once, at the return.

## Approach: sliding-window (Window with a count per fruit type)

### Intuition

Keep a window `[left, right]` with at most two types and a count of each type in it. Extend on the right; when a third type enters, drop trees on the left until a type's count reaches zero and only two types remain. The window is always the longest valid one ending at `right`.

### Algorithm

1. Start with an empty map `inWindow`, `left = 0`, `best = 0`.
2. For each `right`: increment the count of `fruits[right]`. While the map has more than two keys, decrement the count of `fruits[left]`, delete it at zero, and increase `left`. Update `best` with `right - left + 1`.
3. Return `best`.

### Correctness

Invariant: after step 2, the map holds the exact counts of the types in `fruits[left .. right]`, at most two of them, and `left` is the smallest start for which `fruits[left .. right]` has at most two types. Moving `left` further left would bring back a third type, since the loop stopped as soon as one type left completely. So the window is the longest valid run ending at `right`, and the maximum over `right` is the answer.

### Complexity

- Time: O(n) — every tree enters and leaves the window once; map operations are O(1) on average.
- Space: O(1) — the map holds at most three keys at any time.

### Trade-offs

The general "at most k distinct" sliding window: change the `2` to `k` and it solves the k-basket version with O(k) space. It does a few hash operations per tree; `last-run` avoids the map entirely for k = 2.

### Pitfalls and edge cases

- Delete a type whose count drops to zero; otherwise the map size never shrinks and the loop runs to the right edge.
- Shrink with `while`, not `if`: several trees of the type being removed may need to leave.

### Language notes

- Python: a `dict` with `get(..., 0) + 1`; `del` removes a type at zero.
- TypeScript: `Map<number, number>`; `?? 0` handles a missing key, and `size` counts keys.
- Java: `Map.merge(key, 1, Integer::sum)` increments; `merge(key, -1, Integer::sum)` returns the new count, which is boxed, so comparing it with `== 0` unboxes it safely.
- Kotlin: `HashMap.merge(key, 1, Int::plus)` mirrors the Java idiom.
- Go: `inWindow[fruit]++` needs no existence check, because a missing key reads as 0, and `delete` drops a type whose count reaches zero so that `len(inWindow)` counts the distinct types.
- Rust: `entry(fruit).or_insert(0)` adds a type, `get_mut` lends the count for the decrement, and `remove` drops a type at zero; the borrow of the count has ended by the time `remove` runs, so the borrow checker accepts both calls on the same map. The window size is written `right + 1 - left` so it cannot underflow `usize`.

## Approach: last-run (Track the last two types and the final run)

### Intuition

With exactly two baskets, a valid window ending at `right` holds the last type seen and one other type. When a third type arrives, the new window can only keep the trees of the last type that sit immediately before it, that is, the final run of that type. So remember `last` (the type of the previous tree), `beforeLast` (the other type in the window) and `lastRun` (how many trees at the end of the window have type `last`).

### Algorithm

1. Set `window = 0`, `best = 0`, `last = beforeLast = -1`, `lastRun = 0`.
2. For each `fruit`:
   1. If `fruit` is `last` or `beforeLast`, set `window = window + 1`; otherwise set `window = lastRun + 1`.
   2. If `fruit == last`, increase `lastRun`; otherwise set `beforeLast = last`, `last = fruit`, `lastRun = 1`.
   3. Update `best` with `window`.
3. Return `best`.

### Correctness

Invariant: after each tree, `window` is the length of the longest valid run ending there, its two types are `last` and `beforeLast` (or fewer), and its final `lastRun` trees have type `last`. A tree of one of the two types extends that run. A tree of a third type cannot coexist with `beforeLast`, so the longest valid run ending at it consists of the final run of `last` plus the new tree: `lastRun + 1`. Step 2.2 then updates which type is last and how long its final run is.

### Complexity

- Time: O(n) — one pass, O(1) per tree.
- Space: O(1) — five integers.

### Trade-offs

No map, no inner loop, one pass: the leanest solution, and a nice demonstration that a window's left edge can be implied by state instead of stored. It is specific to two types; for `k` baskets you would need the last `k - 1` runs, and the map-based window is simpler.

### Pitfalls and edge cases

- A third type restarts the window at the final run of `last`, not after the first type: in `[0, 0, 1, 1, 1, 2]` the new window is `[1, 1, 1, 2]`.
- When `fruit == beforeLast`, the types swap roles: `beforeLast` becomes the old `last` and `lastRun` resets to 1.
- Initialize the types to a value that is not a valid type (-1), so the first tree starts a fresh window of length 1.

### Language notes

- Python: the tuple assignment `before_last, last = last, fruit` updates both types at once.
- TypeScript: a conditional expression sets `window` in one line; all values are small integers.
- Java: the same single pass over an `int[]` with a ternary for `window`.
- Kotlin: `if` is an expression, so `window = if (...) window + 1 else lastRun + 1`.
- Go: five `int` variables and no map: the constant `empty = -1` stands for an unused basket, and `beforeLast, last = last, fruit` shifts the two types in one assignment.
- Rust: the same five variables. The window is chosen with an `if` expression, and `before_last = last; last = fruit;` shifts the two types in two statements, because Rust has no tuple assignment to existing variables that reads as clearly.
