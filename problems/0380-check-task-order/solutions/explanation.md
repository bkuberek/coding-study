# Check Task Order: Explanation

## Overview

n is the number of tasks and m the number of prerequisite pairs. An order is valid when it is a permutation of the tasks `0` to `n - 1` and every pair `[before, after]` has `before` at an earlier position than `after`. Both approaches check these two conditions; they differ in how they find positions.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-positions | brute | O(n^2 + m * n) | O(1) | a direct reading of the rules, or as an oracle |
| position-table | optimal | O(n + m) | O(n) | default answer |

If the pairs contain a cycle, both approaches answer `false` for every order, because no order can put every task after the one before it all the way around the cycle.

## Approach: scan-positions (Scan the order for the places of both tasks of every pair)

### Intuition

Read the statement literally. To know whether an order lists every task once, count how often each task appears. To know whether a pair is respected, look up where its two tasks stand by walking through the order until each is found, and compare the places.

### Algorithm

1. If `order` does not have exactly `n` entries, return `false`.
2. For every task `t` from 0 to `n - 1`, count how many times `t` appears in `order`; if the count is not 1, return `false`.
3. For every pair `[before, after]`, find the position of `before` and the position of `after` by scanning `order` from the start; if `before` is not earlier, return `false`.
4. Return `true`.

### Correctness

Step 2 makes sure that each of the n task numbers appears exactly once, and with n entries that is a permutation of the tasks, which is condition 1. After it, a scan for any task in range always finds it. Step 3 compares the first and only positions of the two tasks of each pair, which is condition 2. The answer is `true` exactly when neither step found a problem.

### Complexity

- Time: O(n^2 + m * n) — step 2 scans the order once per task, and step 3 scans it up to twice per pair.
- Space: O(1) — only counters and positions.

### Trade-offs

It needs no extra memory and follows the statement closely, which makes it the oracle. Each lookup is a search, though, so with thousands of tasks and pairs it does millions of comparisons that the position table avoids.

### Pitfalls and edge cases

- Check the length first: an order that is shorter than `n` leaves a task out, and one that has repeats cannot hold every task.
- A pair needs `before` strictly earlier than `after`; equal positions cannot happen once the order lists each task once, but `>=` states the failing condition without relying on that.
- An empty order is invalid, because `n` is at least 1.
- A cycle needs no special handling: one pair on it is always broken.

### Language notes

- Python: `order.count(task)` and `order.index(before)` are the scans; both walk the list from the start.
- TypeScript: `filter(..).length` counts a task, and `indexOf` finds its position.
- Java: two small helpers, `occurrences` and `indexOf`, spell out the scans on the `int[]`.
- Kotlin: `count { it == task }` and `indexOf` do the scans on the `IntArray`.
- Go: the same two helpers as in Java, as plain loops over the slice.
- Rust: `iter().filter(..).count()` counts a task and `iter().position(..)` returns the place as an `Option<usize>`; the two options are compared directly, since both are `Some` once the order is known to hold every task.

## Approach: position-table (Record every task's place once and compare it for each pair)

### Intuition

The slow part is looking up a task's place again and again. Look at each entry of the order once, and write its place in an array indexed by task number. The same pass finds repeated tasks, because a task whose slot is already filled has been seen before. After that, the place of any task is one array read, and each pair costs one comparison.

### Algorithm

1. If `order` does not have exactly `n` entries, return `false`.
2. Create `position` with n entries, all set to -1.
3. For each index `i` of `order`, with task `t = order[i]`: if `position[t]` is not -1, return `false`; otherwise set `position[t] = i`.
4. For every pair `[before, after]`, if `position[before] >= position[after]`, return `false`.
5. Return `true`.

### Correctness

Step 3 never writes to a slot twice, so after it the order has n entries with no repeat. Because all n entries are numbers from 0 to n - 1 (by the constraints) and none repeats, every task appears exactly once and `position` holds each task's only place. Step 4 then compares the places that the definition uses, so the result is `true` exactly when both conditions hold.

### Complexity

- Time: O(n + m) — one pass over the order and one pass over the pairs, each step taking constant time.
- Space: O(n) — the `position` array.

### Trade-offs

Linear instead of quadratic, for the price of an array of n integers. The idea is to turn "where is this item" into a table lookup. Producing a valid order from the pairs, rather than checking one, is the topological sort, and a checker like this one can test its output.

### Pitfalls and edge cases

- Use -1, or another marker that is not a valid position, for "not seen"; position 0 is a real place, so 0 cannot mean "unseen".
- Check the length of the order before indexing, so that an order longer than `n` cannot be mistaken for a valid one.
- Tasks that appear in no pair are still part of the order, so they still count towards the length and repeat check.
- Compare with `>=`, not `>`, for the failing test: a pair whose tasks share a place would otherwise pass.

### Language notes

- Python: `[-1] * n` builds the table and `all(...)` with a generator checks the pairs, stopping at the first broken one.
- TypeScript: `new Array<number>(n).fill(-1)` builds the table.
- Java: `Arrays.fill(position, -1)` sets the marker, since `new int[n]` starts at 0.
- Kotlin: `IntArray(n) { -1 }` builds the table with the marker already in it, and `all` checks the pairs.
- Go: `make([]int, n)` starts at 0, so a loop sets every entry to -1 before the pass.
- Rust: a `Vec<Option<usize>>` holds `None` for "not seen", which avoids a sentinel number; `Option<usize>` values compare with `<`, and the pass has filled every slot by the time the pairs are compared. Task numbers arrive as `i32` and are cast to `usize` for indexing.
