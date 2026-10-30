# Single-Threaded CPU: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan | brute | O(n^2) | O(n) | a direct simulation of the rules; small inputs |
| sort-and-heap | optimal | O(n log n) | O(n) | default answer |

`n` is the number of tasks. Both approaches simulate the CPU with a clock; they differ in how they find the next task. The scan looks at every unprocessed task each time; the heap keeps the arrived ones ordered by `(processingTime, index)`.

## Approach: scan (Scan every waiting task before each pick)

### Intuition

Follow the policy literally. At the current time, look at every task that has arrived and is not done yet, and pick the one with the shortest processing time, breaking ties by index. If none has arrived, move the clock to the earliest future arrival.

### Algorithm

1. Set `time = 0`; all tasks are unprocessed.
2. While tasks remain:
   1. Scan the unprocessed tasks in index order; among those with `enqueueTime <= time`, keep the one with the smallest processing time (a strict comparison keeps the smaller index on ties).
   2. If none qualifies, set `time` to the smallest `enqueueTime` among the unprocessed tasks and repeat the scan.
   3. Otherwise mark the chosen task done, append its index, and add its processing time to `time`.

### Correctness

Each pick happens exactly when the CPU becomes idle (at time 0, at the end of a task, or at the next arrival after an idle stretch), and it considers exactly the tasks the policy considers available: arrived by `time` and not yet run. Scanning in index order with a strict `<` selects the smallest `(processingTime, index)` pair, which is the policy's choice. Jumping to the earliest future arrival is exactly what an idle CPU does.

### Complexity

- Time: O(n^2) — each of the n picks scans up to n tasks.
- Space: O(n) — the list (or flags) of unprocessed tasks and the output.

### Trade-offs

Easy to check against the statement, which makes it the oracle. Quadratic work makes it unusable at 10^5 tasks: at 10^4 tasks Python already needs several seconds.

### Pitfalls and edge cases

- Ties go to the smaller index, not to the earlier arrival (case `h5`).
- A task that arrives exactly when another finishes is available for the next pick (`<=`, not `<`).
- The clock can exceed `2^31 - 1` (case `h6`): Java and Kotlin keep it in a `long`.

### Language notes

- Python: removing the chosen index with `list.pop(position)` keeps the remaining indexes in ascending order.
- TypeScript: `splice(best, 1)` removes and returns the chosen index; the scan tracks the next arrival itself rather than spreading 10^5 values into `Math.min`, which can exceed the engine's argument limit.
- Java and Kotlin: a `boolean[]` of finished tasks avoids list removals; the same pass computes the next arrival for idle stretches.
- Go: `int` is 64 bits, so the clock can pass 2^31 - 1 without a wider type. `slices.Delete(remaining, best, best+1)` removes one element and shifts the tail, keeping the indexes ascending like Python's `list.pop(position)`; it is O(n), as the scan already is.
- Rust: the clock is an `i64`, because the sum of up to 10^5 processing times of 10^9 each does not fit an `i32`; the task fields are widened with `i64::from`. The pick is `filter` then `min_by_key`, which returns the first of several equal minimums, so on equal processing times the smaller index (earlier in `remaining`) wins, as the strict `<` does in the other languages. `Vec::remove(best)` keeps the order.

## Approach: sort-and-heap (Sort by arrival, pick from a min-heap of arrived tasks)

### Intuition

Two orders matter: tasks join the waiting pool in order of enqueue time, and leave it in order of `(processingTime, index)`. Sort the indexes by enqueue time once, then walk that list with a pointer, pushing every task that has arrived into a min-heap keyed by `(processingTime, index)`. Each pick is one pop.

### Algorithm

1. Sort the task indexes by enqueue time.
2. Set `time = 0`, `next = 0` (the next task to arrive), and an empty min-heap `waiting`.
3. Repeat n times:
   1. If `waiting` is empty and the next task arrives after `time`, jump `time` to its enqueue time.
   2. Push every task with `enqueueTime <= time` from the sorted list into `waiting`.
   3. Pop the smallest `(processingTime, index)`, append the index, and add its processing time to `time`.

### Correctness

Invariant: before each pick, `waiting` holds exactly the tasks that have arrived by `time` and are not processed, because step 3.2 admits arrivals in enqueue order up to the current time and each processed task left the heap when it was popped. The heap's minimum is then exactly the task the policy starts. Step 3.1 handles an idle CPU: when nothing waits, the policy waits for the next arrival, and after the jump step 3.2 admits it (and anything arriving at the same moment), so the heap is never empty when popped.

### Complexity

- Time: O(n log n) — sorting is O(n log n), and each task is pushed and popped once at O(log n).
- Space: O(n) — the sorted index array and the heap.

### Trade-offs

The standard answer: two classic structures, each doing what it is good at. It is the same pattern as many scheduling simulations (meeting rooms, process schedulers): an arrival-ordered list plus a priority queue of what is ready.

### Pitfalls and edge cases

- The heap key must include the index as a tie-breaker; a heap ordered by processing time alone returns equal tasks in an arbitrary order.
- Jump the clock only when the heap is empty; jumping while tasks wait would skip them.
- Use a 64-bit clock in Java and Kotlin; TypeScript numbers are exact up to 2^53, far above the largest possible clock of 10^14.

### Language notes

- Python: tuples `(processing_time, index)` compare lexicographically, which is exactly the tie-break rule, so `heapq` needs no custom key.
- TypeScript: no built-in priority queue, so the reference implements a min-heap of indexes with a `before` comparison on `(processingTime, index)`; the class assigns its field in the constructor because parameter properties are not erasable syntax.
- Java: `Comparator.<Integer>comparingInt(i -> tasks[i][1]).thenComparingInt(i -> i)` builds the two-level key; the explicit type witness is needed for the chained call to infer `Integer`.
- Kotlin: `compareBy<Int> { tasks[it][1] }.thenBy { it }` builds the same comparator; `tasks.indices.sortedBy { tasks[it][0] }` produces the arrival order.
- Go: `container/heap` needs a type that implements `heap.Interface`, so the reference declares `shortestFirst []waitingTask`, and its `Less` compares the processing time and then the index, which is the tie-break written out. The arrival order comes from `slices.SortFunc` with `cmp.Compare` on the enqueue times.
- Rust: `BinaryHeap<Reverse<(i32, usize)>>` is a min-heap of `(processing time, index)` tuples, and tuples compare field by field, so the tie-break needs no comparator. `sort_by_key` orders the indexes by enqueue time, and `time.max(..)` is the idle jump.
