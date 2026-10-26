# Open the Lock: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bfs | optimal | O(S·W + d) | O(S + d) | default answer |
| bidirectional-bfs | optimal | O(S·W + d) | O(S + d) | the state space is large and both ends are known; often explores far fewer states |

The lock has S = 10^4 settings, and each setting has exactly 2·W = 8 neighbors for W = 4 wheels. The dead ends (d of them) are settings the search may never enter. The fewest moves is a shortest path in this unweighted graph. Both approaches are breadth-first searches; the bidirectional one grows two smaller searches instead of one large one.

## Approach: bfs (Breadth-first search over lock settings)

### Intuition

Every move costs one, so explore the settings in order of distance from `"0000"`: first all settings one move away, then all settings two moves away, and so on. The level at which the target first appears is the answer. Dead ends are simply settings that may never be visited, so putting them in the visited set up front keeps the search out of them with no extra check.

### Algorithm

1. Put all dead ends in a set `seen`. If `"0000"` is in it, return -1.
2. Add `"0000"` to `seen` and start the first level with it, at `moves = 0`.
3. While the level is not empty: if it contains the target, return `moves`. Otherwise build the next level from the eight turns of every setting in the level, keeping only settings not yet in `seen` (and adding them to `seen`), and add 1 to `moves`.
4. Return -1.

### Correctness

Breadth-first search visits settings level by level, and each level holds exactly the settings whose shortest dead-end-free distance from `"0000"` is `moves`: a setting first appears in the level after the earliest level that holds one of its neighbors. So the first level containing the target gives its shortest distance. A dead end is never added to a level, so no sequence through a dead end is ever counted. If the levels run out, the target is not reachable without passing a dead end.

### Complexity

- Time: O(S·W + d) — building the set costs O(d); each of at most S settings is expanded once and produces 2·W turns of W characters each, which is a constant for four wheels.
- Space: O(S + d) — the visited set holds the dead ends and every visited setting; a level holds at most S settings.

### Trade-offs

The standard answer: simple, and fast because the state space is only 10^4. Generating neighbors as strings is easy to read; encoding settings as integers 0 to 9999 and using a boolean array instead of a hash set is several times faster if it matters.

### Pitfalls and edge cases

- Check `"0000"` against the dead ends before anything else; if it is one, even target `"0000"` is unreachable.
- Turning down from 0 gives 9: use `(digit + 9) % 10`, not `digit - 1`.
- Target `"0000"` (when it is not a dead end) needs zero moves.
- Mark settings as seen when they are added to a level, not when they are expanded, or the same setting is generated many times.

### Language notes

- Python: `collections.deque` holds `(setting, moves)` pairs; the turns are built by string slicing.
- TypeScript: each level is an array; `Number(setting[wheel])` reads a digit, and string `slice` builds the neighbor.
- Java: `Set.add` returns `false` for a setting already seen, which doubles as the visited check; neighbors are built by changing one char of a `char[]` and copying it into a new `String`.
- Kotlin: a whole level is produced in one expression, `level.flatMap(::turns).filter(seen::add)`, where `seen::add` both checks and marks.

## Approach: bidirectional-bfs (Grow searches from both ends and meet in the middle)

### Intuition

A breadth-first search from the start explores a ball of settings around it that keeps growing until it touches the target. Moves can be undone, so the graph is undirected and a second search can grow from the target at the same time. When the two balls touch, the path through the meeting point is a shortest one. Two balls of radius `k/2` are usually much smaller than one ball of radius `k`.

### Algorithm

1. Put the dead ends in `blocked`. If `"0000"` is blocked, return -1; if the target is `"0000"`, return 0.
2. Start the frontiers `near = {"0000"}` and `far = {target}`, mark both as seen, and set `moves = 0`.
3. While both frontiers are non-empty:
   1. If `near` is larger than `far`, swap them, so the smaller one grows.
   2. Add 1 to `moves` and build the next level of `near`: for every turn of every setting in it, if the turn is in `far`, return `moves`; otherwise keep it if it is neither seen nor blocked, marking it seen.
4. Return -1.

### Correctness

Each frontier holds the settings at one distance from its own end (start or target), and `moves` is the number of levels expanded on both sides together. When the search stops, the setting being expanded lies `a` moves from one end and the turn it found lies in the other frontier, `b` moves from the other end, with `a + 1 + b = moves`: that is a real path. It is also a shortest one. Until a meeting is found, the two explored regions are disjoint and no move links the two frontiers, so every path from start to target still has a stretch outside both regions and is longer than `moves`; when the levels expanded add up to the shortest length `L`, the shortest path must cross from one region straight into the other frontier, and the expansion that completes level `L` finds that move. A setting claimed by one side is never claimed by the other, which is why one shared seen set suffices. If a frontier empties, everything reachable from its end was explored without touching the other side, so no path exists.

### Complexity

- Time: O(S·W + d) — the same worst case as the plain search, since every setting is still expanded at most once; in typical cases each side explores a much smaller ball.
- Space: O(S + d) — the seen set, the dead ends and two frontiers.

### Trade-offs

Same worst case, usually far less work, at the price of trickier bookkeeping: two frontiers, a swap, and a meeting test. On this small lock the gain is a constant factor; on graphs whose levels grow quickly (word ladders, larger locks) it is the difference between feasible and not. It needs the target in advance and an undirected (reversible) move set.

### Pitfalls and edge cases

- Test for a meeting before the `seen` check: the meeting setting belongs to the other frontier, so it is already seen.
- Expand one whole level at a time; mixing levels breaks the distance count.
- Handle `target == "0000"` before starting, since the frontiers would otherwise begin equal.

### Language notes

- Python: frontiers are sets, swapped with a tuple assignment.
- TypeScript: `Set<string>` frontiers swapped with `[near, far] = [far, near]`; the target check uses `far.has(...)`.
- Java: `HashSet` frontiers swapped through a temporary; `List.of` builds the initial sets.
- Kotlin: `near = far.also { far = near }` swaps the two frontiers in one line; `seen.add(...)` returns whether the setting was new.
