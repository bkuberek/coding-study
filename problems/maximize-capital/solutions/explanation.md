# Maximize Capital: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan | brute | O(k n) | O(n) | tiny inputs, or as an oracle |
| sort-and-heap | optimal | O(n log n + k log n) | O(n) | default answer |

`n` is the number of projects and `k` the number of picks. Both approaches apply the same greedy rule: in every round, take the most profitable project you can afford. They differ in how they find it.

## Approach: scan (Scan for the most profitable affordable project in every round)

### Intuition

Apply the greedy rule literally: in each of the `k` rounds, look at every project not yet done, keep the affordable one with the largest profit, and complete it. If nothing is affordable, the capital can never grow again, so stop.

### Algorithm

1. Mark every project as unused.
2. Repeat up to `k` times:
   1. Among unused projects with `capital[i] <= w`, find the one with the largest profit.
   2. If there is none, stop.
   3. Mark it used and add its profit to `w`.
3. Return `w`.

### Correctness

The greedy choice is safe. Let `p` be the most profitable affordable project in some round, and take any optimal plan from that round on. If the plan picks `p` later or never, replace its first pick `q` (also affordable now, so `profit(q) <= profit(p)`) by `p`, and if `p` appeared later, put `q` there instead. After the swap, the capital at every later step is at least as large as before, because capital only grows and `p` earns at least as much as `q`; so every later pick of the plan stays affordable and the final capital does not decrease. By induction over the rounds, picking greedily is optimal. Stopping when nothing is affordable is correct, because without a pick the capital stays the same, and so does the set of affordable projects.

### Complexity

- Time: O(k n) — each round scans all n projects. With `k` proportional to `n`, as in the generated cases, it is quadratic.
- Space: O(n) — the used flags.

### Trade-offs

The shortest correct code and an exact check of the greedy rule, which makes it the oracle. It repeats almost the same scan every round, although only the newly affordable projects change between rounds.

### Pitfalls and edge cases

- Starting a project does not spend capital; subtracting `capital[i]` from `w` is a different problem.
- Zero-profit projects can be picked, but they never unlock anything (case `h3`).
- Stop early when nothing is affordable instead of looping uselessly through the remaining rounds.

### Language notes

- Kotlin: `repeat(k)` with a `return funds` inside the lambda leaves the whole function, because `repeat` is an inline function, so a non-local return is allowed.
- Go: `for range k` repeats the body `k` times (range over an integer, Go 1.22), and `break` leaves that loop directly. Go's `int` is 64 bits, so the running capital needs no widening.
- Rust: the parameters are owned, so `mut w` updates the capital in place. The scan keeps `best_profit` next to `best` (profits are never negative, so `-1` means "none yet"), which makes the strict `>` of the other languages a plain comparison and avoids `Option` combinators. The capital never exceeds 10^9 + 10^5 * 10^4, inside `i32`.

## Approach: sort-and-heap (Sort by required capital, pick from a max-heap of affordable profits)

### Intuition

Two orders matter. Projects become affordable in order of increasing requirement, and capital only grows, so a single pointer over the projects sorted by requirement finds every newly affordable one, and none ever becomes unaffordable again. Among the affordable projects, the greedy pick is the largest profit, which a max-heap delivers in O(log n).

### Algorithm

1. Sort the projects by required capital.
2. Repeat up to `k` times:
   1. Advance the pointer over every project with requirement at most `w`, pushing its profit into a max-heap.
   2. If the heap is empty, stop.
   3. Pop the largest profit and add it to `w`.
3. Return `w`.

### Correctness

Invariant: at the start of each pick, the heap holds the profits of exactly the affordable projects that have not been completed. The pointer admits projects in order of requirement while the requirement is at most the current capital, and because capital never decreases, an admitted project stays affordable. Popping the maximum is therefore the greedy choice, which the exchange argument in the scan approach shows to be optimal.

### Complexity

- Time: O(n log n + k log n) — sorting is O(n log n); each project is pushed at most once and each round pops once, both O(log n).
- Space: O(n) — the sorted projects and the heap.

### Trade-offs

The standard answer, built from the same pattern as `single-threaded-cpu`: an arrival order handled by sorting and a pointer, plus a priority queue of what is ready. The heap only ever holds affordable projects, so it does no wasted comparisons on out-of-reach ones.

### Pitfalls and edge cases

- Sort the requirement and the profit together; sorting the two arrays separately breaks the pairing.
- Push all newly affordable projects before each pop, not just one; a single pick can unlock many projects at once.
- When the heap is empty, the answer is final: later rounds cannot change it.

### Language notes

- Python: `sorted(zip(capital, profits))` sorts the pairs by requirement, and `heapq` stores negated profits to act as a max-heap.
- TypeScript: no built-in priority queue, so the reference implements a small max-heap; the projects are sorted as an index array keyed by `capital`.
- Java: an `int[][]` of `{capital, profit}` pairs sorted with `Comparator.comparingInt`, and a `PriorityQueue<Integer>` with `Comparator.reverseOrder()`; `poll` unboxes into the `int` sum.
- Kotlin: `profits.indices.sortedBy { capital[it] }` gives the arrival order; `affordable.poll() ?: return funds` ends the function when the heap is empty, because `poll` returns null there.
- Go: a small `project` struct pairs each requirement with its profit, sorted with `slices.SortFunc` and `cmp.Compare`. `container/heap` needs a type that implements `heap.Interface`, so the reference declares `maxHeap []int` with `Less` as `>`, and `heap.Pop(affordable).(int)` asserts the stored type back.
- Rust: `capital.into_iter().zip(profits)` builds the `(capital, profit)` pairs, and tuples sort field by field, like Python's `sorted(zip(..))`. `BinaryHeap<i32>` is already a max-heap, so no negation is needed, and `let Some(profit) = affordable.pop() else { break }` is the empty-heap exit.
