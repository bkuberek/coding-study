# Task Scheduler: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| heap-simulation | intermediate | O(n log 26) | O(26) | you also need the schedule itself, or the rules get more complex |
| frame-formula | optimal | O(n) | O(26) | default answer when only the length is needed |

`n` is the number of tasks; there are at most 26 labels. Both approaches start from the counts per label. The simulation builds an optimal schedule greedily; the formula counts its length directly.

## Approach: heap-simulation (Simulate: run the most frequent available task, park the rest in a cooldown queue)

### Intuition

In every slot, run the available label with the most copies left. Labels that just ran are parked in a queue until their cooldown is over; since each one returns exactly `cooldown + 1` slots after it ran, the queue is ordered by return time automatically. When no label is available, jump the clock straight to the next return instead of stepping through idle slots.

### Algorithm

1. Count the copies per label; put the counts into a max-heap `ready`.
2. Set `time = 0` and an empty FIFO queue `cooling` of `(return time, remaining count)`.
3. While `ready` or `cooling` is non-empty:
   1. If `ready` is non-empty, pop the largest count, run one copy in slot `time`; if copies remain, enqueue `(time + cooldown + 1, count - 1)`. Advance `time` by 1.
   2. Otherwise set `time` to the return time at the front of `cooling` (the skipped slots are idle).
   3. Move every queued label whose return time is at most `time` back into `ready`.
4. Return `time`.

### Correctness

Validity: a label re-enters `ready` only at its return time, `cooldown + 1` slots after its last run, so the rule is never broken, and every copy of every label is run exactly once.

Optimality: the frame-formula section shows that no schedule is shorter than `max(n, (top - 1) * (cooldown + 1) + tied)`. The greedy schedule reaches that bound. A label with the most copies left is never passed over while it is available, so the most frequent labels run exactly `cooldown + 1` slots apart, which makes the frames as short as the rule allows. The slot is left idle only when every unfinished label is cooling down. If that ever happens, the frames are not full, and the schedule ends one slot after the last run of the most frequent labels, which is the frame bound. Otherwise no slot is idle and the length is `n`. Jumping the clock produces exactly the idle slots that stepping one slot at a time would. The oracle cross-check of this simulation against the formula on random inputs tests the same claim empirically.

### Complexity

- Time: O(n log 26) — each task is popped and pushed once, on a heap of at most 26 counts; idle stretches cost O(1) each because the clock jumps. That is linear in n.
- Space: O(26) — the heap and the queue hold at most one entry per label.

### Trade-offs

Direct and easy to argue, and it extends to variants where the formula breaks (per-label cooldowns, tasks of different lengths, reporting the actual schedule). It is an independent check of the formula, which is why it is the oracle here. For the plain question it does more work than needed.

### Pitfalls and edge cases

- A label may run again at `time + cooldown + 1`, not `time + cooldown`: the cooldown counts the slots strictly between two runs.
- Stepping through idle slots one by one is correct but costs O(n * cooldown) in the worst case; jumping to the next return avoids it.
- Release labels from the queue after advancing the clock, so a label whose cooldown just ended is available in the very next slot.

### Language notes

- Python: `heapq` is a min-heap, so counts are stored negated; `count + 1` on a negated count means one copy fewer. `collections.deque` gives O(1) `popleft`.
- TypeScript: no priority queue or deque in the standard library; the reference uses a small max-heap and an array with a moving `head` index as a queue, because `Array.prototype.shift` is O(n).
- Java: `PriorityQueue<>(Comparator.reverseOrder())` is the max-heap; the queue holds `int[]` pairs in an `ArrayDeque`. `task - 'A'` turns a label into an index.
- Kotlin: `kotlin.collections.ArrayDeque<Pair<Int, Int>>` and `to` for pairs; `Char - Char` yields an `Int`, so `task - 'A'` indexes the count array.

## Approach: frame-formula (Count frames around the most frequent task)

### Intuition

Let the most frequent label occur `top` times. Between two of its runs there must be at least `cooldown` other slots, so its runs cut the schedule into `top - 1` frames of `cooldown + 1` slots, plus a final frame that contains its last run. Every other label with `top` copies also needs a slot in that final frame. Everything else fits into the gaps of the frames; if it overflows them, the frames simply get longer and no slot is idle, so the answer is the number of tasks.

### Algorithm

1. Count the copies per label; let `top` be the largest count and `tied` the number of labels with that count.
2. Return `max(n, (top - 1) * (cooldown + 1) + tied)`.

### Correctness

Lower bounds: any schedule has at least `n` slots, and the `top` runs of a most frequent label span at least `(top - 1) * (cooldown + 1) + 1` slots; each of the other `tied - 1` labels with `top` copies must also run after the start of the last frame, which adds one slot each. Achievability: fill frame `i` with the `i`-th copy of each label in order of decreasing count. Labels with fewer than `top` copies never land twice in one frame and are at least `cooldown + 1` apart, because consecutive copies sit in consecutive frames. If the other tasks do not fill the gaps, the remaining gaps are idle and the length is the frame bound; if they overflow, the frames are extended with no idle slot, and the length is `n`. The answer is the larger of the two bounds.

### Complexity

- Time: O(n) — one pass to count; the rest scans 26 counters.
- Space: O(26) — the counters.

### Trade-offs

A one-line answer after counting, and the fastest possible. It is easy to misremember (`top - 1` frames, `+ tied`, and the `max` with `n`), so derive it from the frames in an interview rather than reciting it. It does not produce a schedule, and it no longer holds when tasks have different lengths or cooldowns.

### Pitfalls and edge cases

- Forgetting `max(n, ...)`: with many distinct labels the frame bound is smaller than the number of tasks.
- Forgetting `tied`: two labels with `top` copies both need a slot in the last frame.
- `cooldown = 0` gives `top + tied - 1 <= n`, so the answer is `n`, as it should be.

### Language notes

- TypeScript: `Math.max(...counts)` spreads only 26 values here, so it cannot hit the argument-count limit that spreading a large array would.
- Java: one pass over the counts tracks both the maximum and how many labels reach it.
- Kotlin: `IntArray.max()` and `count { it == top }` read the two numbers directly.
