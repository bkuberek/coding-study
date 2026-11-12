# Village Paths

## Statement

A region has `villages` villages, numbered from `0`. At the start there are no paths, so every village is on its own. Footpaths are then built one at a time, and a footpath can be walked in both directions. Two villages belong to the same **group** when you can walk from one to the other, either on one footpath or by passing through other villages on the way. A village that no footpath touches is a group of one.

Design a class `VillageMap` that keeps track of the groups while paths are added, and answers questions in between.

**The technique: union-find.** Groups here only ever merge, they never split: a footpath cannot be un-built. A structure that tracks groups under merges only is called **union-find** or a **disjoint-set** structure, because the groups share no village (they are disjoint). It does two things: *union* merges the groups of two villages, and *find* answers which group a village is in, in a way that lets you compare two villages. With a good design both are almost instant, even for a hundred thousand villages.

Here is a small run with five villages. The braces show the groups after each step:

```text
start                {0} {1} {2} {3} {4}      5 groups
addPath(0, 1)        {0, 1} {2} {3} {4}       joined two groups: true
addPath(2, 3)        {0, 1} {2, 3} {4}        joined two groups: true
addPath(1, 0)        {0, 1} {2, 3} {4}        already together:  false
addPath(1, 2)        {0, 1, 2, 3} {4}         joined two groups: true
canReach(0, 3)       true
canReach(0, 4)       false
groupSize(3)         4                        the group {0, 1, 2, 3}
groupCount()         2
```

## Input

- `VillageMap(villages)`: creates a map of `villages` villages with no paths.
- `addPath(a, b)`: builds a footpath between villages `a` and `b`, and returns `true` if it joined two different groups. If `a` and `b` were already in the same group (which includes `a == b`), nothing changes and it returns `false`.
- `canReach(a, b)`: returns `true` if the villages `a` and `b` are in the same group. A village always reaches itself.
- `groupSize(village)`: returns how many villages are in the group of `village`, itself included.
- `groupCount()`: returns the number of groups in the whole region.

Each test case is a sequence of operations: the first creates the map, and the following ones call its methods.

## Output

For each operation, its return value: `null` for the constructor, `true` or `false` for `addPath` and `canReach`, and a number for `groupSize` and `groupCount`.

## Examples

### Example 1

<!-- case: ex1 -->

This is the run above. The third path, `addPath(1, 0)`, finds villages 0 and 1 already in one group, so it returns `false` and nothing changes. The fourth joins `{0, 1}` with `{2, 3}`, so village 3 is reachable from village 0 while village 4 is not, and village 3 sits in a group of size 4 among two groups in total.

### Example 2

<!-- case: ex2 -->

Before any path exists, each of the four villages is its own group. The path `2-0` joins `{2, 3}` with `{0, 1}`, which makes villages 1 and 3 reachable from each other, and leaves a single group of size 4.

## Constraints

- `1 <= villages <= 10^5`
- `0 <= a, b, village < villages`; `a` and `b` may be equal.
- At most `10^5` calls to `addPath`, `canReach`, `groupSize` and `groupCount` in total.

## Follow-ups

- Why must the class never need to un-build a path, and which part of your design would break if it had to?
- How would you also report the size of the largest group, in constant time?
- The problem Count Connected Components gives you all the paths at once and asks for the number of groups. How does that problem use this class?

## Hints

### Hint 1

Start with the plainest bookkeeping: an array `label` with one entry per village, saying which group the village is in, where everyone begins with their own label. Which of the four questions can you answer from this array immediately, and what does `addPath` have to change when two groups join?

### Hint 2

Relabelling a whole group makes `addPath` slow for big groups. Store something cheaper at each village: the name of another village in the same group that it points to, or itself if it points to nobody. Follow the pointers from any village and you arrive at one special village that points to itself, the group's leader. Two villages are in the same group exactly when they lead to the same leader.

### Hint 3

Joining two groups only needs one leader to point at the other. Keep each group's size at its leader and point the smaller group's leader at the larger one's, so that chains of pointers stay short. When you follow pointers from a village, also redirect every village you passed straight to the leader, so the next search from any of them is a single step.
