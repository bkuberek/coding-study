# Debug: Grid Aliasing: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| snapshot-copy | intermediate | O((mn)^2) | O(mn) | the minimal fix: the shipped design with both aliasing bugs removed |
| multi-source-bfs | optimal | O(mn) | O(mn) | a rewrite is allowed: no copies, so nothing to alias |

## Approach: snapshot-copy (Minute-by-minute snapshots with real copies)

### Intuition

There are two bugs, and both are aliasing: two names for one mutable object, where the code assumes two independent objects.

1. **Shared rows in the result.** `[[-1] * cols] * rows` (Python), `new Array(rows).fill(new Array(cols).fill(-1))` (TypeScript), `Arrays.fill(times, unburnt)` (Java) and `Array(rows) { unburnt }` (Kotlin) all build an outer array whose `m` slots point to the *same* row object. Writing `times[r][c]` writes column `c` of every row at once. That is the "every row is identical" complaint: each column ends up holding whichever value was written to it last.
2. **A shallow copy of the simulation state.** `current.copy()`, `[...current]`, `current.clone()` and `current.copyOf()` copy the outer array only. `upcoming` and `current` are different lists of the *same* rows, so marking a cell as burning in `upcoming` also marks it in `current`, in the middle of the scan. A cell that caught fire this minute is then visited later in the same scan and spreads immediately. Fire races right and down (the scan direction) in a single minute, which is why `[[2, 1, 1, 1]]` reports `[[0, 1, 1, 1]]`. The same shallow copy makes the first minute write straight into the caller's `grid`.

The fix is to give every row its own storage: allocate each result row separately, and copy each row of the state.

### Debugging approach

1. **Reproduce the loudest symptom first.** On Example 1 the output has three identical rows. Two bugs are layered here, and the first one hides the second.
2. **Minimize.** A 2 x 2 grid with one burning cell, `[[2, 1], [1, 1]]`, already shows two rows that are equal.
3. **Probe the data structure, not the algorithm.** Write to one cell and print the grid, or compare identities: `times[0] is times[1]` in Python, `times[0] === times[1]` in TypeScript, `times[0] == times[1]` (reference equality) in Java and Kotlin. `True` means aliasing. A debugger shows the same object id on every row.
4. **Fix and rerun.** With independent result rows, Example 1 still fails. The second failure, from the ticket, is `[[2, 1, 1, 1]]`. It is one row, so shared rows cannot explain it.
5. **Trace one minute.** Print `current` after each cell visit during minute 1. Right after `(0, 1)` catches fire in `upcoming`, `current[0][1]` is already `2`, although `current` should be frozen for the whole minute. So `current` and `upcoming` share rows, and the culprit is the copy.
6. **Confirm the side effect.** Print the caller's `grid` after the call. It changed, so it shares rows with `upcoming` too.

### Algorithm

1. Allocate `times` with an independent row per grid row, every cell `-1`. Set `times[r][c] = 0` for every burning cell.
2. Set `current = grid` and `minute = 0`.
3. Repeat while the previous minute set anything on fire:
   1. Increment `minute` and make `upcoming` a deep copy of `current`, copying every row.
   2. For every cell burning in `current`, set each brush neighbor in `current` to burning in `upcoming` and record `times[neighbor] = minute`.
   3. Replace `current` with `upcoming`.
4. Return `times`.

### Correctness

By induction on the minute `t`: at the start of minute `t`, `current` holds exactly the cells burning by minute `t - 1`. The code only reads `current` and only writes `upcoming`, and the two now share no rows, so the cells set on fire during minute `t` are exactly the brush neighbors of cells burning by minute `t - 1`, which is the spreading rule. `times[r][c]` is written once, in the minute the cell first changes from `1` to `2`, because afterwards `current` no longer holds `1` there. Since the rows of `times` are distinct, each write affects only its own cell. The loop stops after the first minute with no new fires; from then on nothing can change. Cells never written keep `-1`. The caller's `grid` is only ever read, because the first write goes to a deep copy.

### Complexity

- Time: O((mn)^2) — each minute copies and scans all mn cells, and the fire can need up to about mn minutes along a winding corridor (test `h14` takes 16 minutes on a 5 x 5 map).
- Space: O(mn) — `times`, `current` and `upcoming`.

### Trade-offs

This is the smallest change that makes the shipped code correct, so it is what a reviewer wants in a bug-fix commit: two lines change and the design stays the same. It is still slow on long corridors because each minute copies the grid. Multi-source BFS (next section) is the better design when a rewrite is in scope. Within the snapshot design, an alternative to deep copies is to collect each minute's new fires in a list and apply them after the scan. That also avoids aliasing, with less copying.

### Pitfalls and edge cases

- The general trap: copying or repeating a container of mutable objects copies references, not the objects. `list * n`, `Array.fill(obj)`, `Arrays.fill(Object[], obj)`, `Array(n) { sameObject }`, `list.copy()`, spread `[...a]`, `clone()` on a 2-D array and `copyOf()` are all shallow.
- A single-row grid hides the shared-row bug. A test that only spreads left or up hides the shallow-copy bug, because the scan has already passed those cells.
- Firebreaks and unreachable brush must stay `-1`. Do not confuse "never burns" with "burns at minute 0".
- Mutating the caller's input is a bug even when the return value is right: the dashboard reuses the terrain map.

### Prevention

- Allocate 2-D structures with a per-row factory: `[[-1] * cols for _ in range(rows)]`, `Array.from({ length: rows }, () => ...)`, `new int[rows][cols]`, `Array(rows) { IntArray(cols) { -1 } }`.
- Add one test with at least two rows that must differ, and one test whose answer depends on a frozen snapshot (fire travelling right or down, as in `h7`).
- Linters help. Pylint has no rule for `[[x] * n] * m`, but code review checklists should. In TypeScript, `fill` with an object argument is worth a lint rule. In Java, prefer `int[][]` allocated in one `new` expression.
- Treat inputs as read-only: make a defensive deep copy, or pass immutable views (`tuple` rows, `ReadonlyArray`) so that an accidental write fails loudly.

### Language notes

- Python: `list * n` repeats references; `copy.copy` and `list.copy` are shallow; `copy.deepcopy` or `[row.copy() for row in grid]` copies the rows.
- TypeScript: `Array.prototype.fill(value)` stores the same `value` object in every slot. `Array.from({ length }, factory)` calls the factory once per slot. Spread and `slice()` are shallow; `structuredClone` is deep.
- Java: `int[][]` is an array of row references. `clone()` copies those references, and `Arrays.fill(Object[] a, Object val)` stores one row everywhere. `new int[rows][cols]` allocates independent rows.
- Kotlin: `Array(n) { x }` evaluates the lambda per slot, but if the lambda returns an existing object, every slot holds that object. `copyOf()` on `Array<IntArray>` is shallow; copy each `IntArray` with `copyOf()`.

## Approach: multi-source-bfs (Multi-source BFS)

### Intuition

The burn time of a cell is its distance, in grid steps through brush, from the nearest initially burning cell. That is a shortest-path question on an unweighted grid, answered by one breadth-first search started from every burning cell at once. BFS settles each cell once, in order of distance, so it needs no per-minute snapshot. Without a copy, there is nothing to alias.

### Algorithm

1. Allocate `times` with independent rows, every cell `-1`.
2. Push every burning cell on a queue and set its time to `0`.
3. While the queue is not empty, pop a cell. For each brush neighbor whose time is still `-1`, set its time to the popped cell's time plus one and push it.
4. Return `times`.

### Correctness

BFS pops cells in non-decreasing order of distance from the source set. When a neighbor is first discovered from a cell at distance `d`, no unsettled cell is closer than `d + 1`, so `d + 1` is the shortest distance through brush. That distance is the minute it catches fire: fire advances exactly one step per minute along every path at once. `times == -1` doubles as the "visited" mark, so each cell is pushed at most once. Cells the search never reaches keep `-1`. `grid` is only read.

### Complexity

- Time: O(mn) — each cell is pushed and popped at most once, with four neighbor checks.
- Space: O(mn) — `times` and the queue.

### Trade-offs

It is asymptotically faster and has no copy to get wrong. It is the expected answer for "rotting oranges" style questions in an interview. It is a bigger diff than the minimal fix, though. In a real bug-fix review, fix the aliasing first and propose the rewrite separately.

### Pitfalls and edge cases

- Seed the queue with *all* sources before the search starts. Running a BFS per source and taking the minimum is correct but O(k·mn).
- Mark a cell when you push it, not when you pop it; otherwise a cell can be queued from several neighbors.
- The result grid still needs independent rows. The first bug is about allocation and applies to any algorithm.

### Language notes

- Python: `collections.deque.popleft` is O(1); `list.pop(0)` is O(n).
- TypeScript: there is no built-in deque, so the reference walks the array with a read index instead of calling `shift()`, which is O(n).
- Java: `ArrayDeque<int[]>` stores the coordinates as small arrays. `ArrayDeque` rejects `null`, which is fine here.
- Kotlin: `kotlin.collections.ArrayDeque` with `Pair<Int, Int>`; destructuring `val (r, c) = queue.removeFirst()` reads well. Each `Pair` allocates and boxes both ints, which is acceptable at 2,500 cells.
