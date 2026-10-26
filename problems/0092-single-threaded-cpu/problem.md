# Single-Threaded CPU

## Statement

A CPU with a single core receives `n` tasks, numbered `0` to `n - 1`. Task `i` is described by `tasks[i] = [enqueueTime, processingTime]`: it becomes available at time `enqueueTime` and needs `processingTime` units of uninterrupted work.

The CPU follows a fixed policy, starting at time 0:

- When it is idle and no task is available, it waits until the next task becomes available.
- When it is idle and at least one task is available, it starts the available task with the **shortest processing time**. If several are tied, it starts the one with the **smallest index**.
- Once started, a task runs to completion without interruption. The moment it finishes, the CPU is idle again and can start another task immediately; a task that becomes available at exactly that moment is considered available.

Return the order in which the CPU processes the tasks, as a list of task indexes.

Reference: this is our own wording of LeetCode problem 1834, [Single-Threaded CPU](https://leetcode.com/problems/single-threaded-cpu/).

## Input

- `tasks`: one `[enqueueTime, processingTime]` pair per task; the position in the array is the task's index.

## Output

The task indexes in processing order; every index appears exactly once.

## Examples

### Example 1

<!-- case: ex1 -->

Task 0 arrives at time 2 and runs alone until time 6. By then tasks 1, 2 and 3 are all waiting, with processing times 3, 1 and 2, so they run shortest first: 2 (until 7), then 3 (until 9), then 1.

### Example 2

<!-- case: ex2 -->

All three tasks arrive together and take equally long, so the smallest index always wins the tie.

## Constraints

- `1 <= tasks.length <= 10^5`
- `1 <= enqueueTime, processingTime <= 10^9`
- The clock can pass `2^31 - 1`: use a 64-bit integer for time where the language needs one.

## Follow-ups

- Scanning all waiting tasks before every pick is quadratic. Which structure returns the shortest waiting task quickly?
- Tasks become available in order of enqueue time, not index. How do you feed them to the CPU at the right moments?
- How would the order change if a newly arrived shorter task could interrupt the running one?

## Hints

### Hint 1

Process the tasks in order of their enqueue time, keeping track of the current time. Before each pick, everything that has arrived by now joins a waiting pool.

### Hint 2

The waiting pool must give you the task with the smallest `(processingTime, index)` pair, again and again, while new tasks keep joining: a min-heap.

### Hint 3

If the pool is empty, jump the clock forward to the next enqueue time instead of stepping through idle time one unit at a time.
