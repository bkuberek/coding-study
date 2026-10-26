# Task Scheduler

## Statement

A single processor has to run a list of tasks. Each task is labelled with an uppercase letter, and tasks with the same label are interchangeable copies of the same job. Every task takes exactly one time slot. In each slot the processor either runs one task or sits idle.

There is one rule: after running a task with some label, the processor must let at least `cooldown` slots pass before it runs another task with the same label. Those slots can be spent on other labels or on idling. You may run the tasks in any order. Return the smallest number of slots needed to finish all of them, counting idle slots.

Reference: this is our own wording of LeetCode problem 621, [Task Scheduler](https://leetcode.com/problems/task-scheduler/).

## Input

- `tasks`: the task labels, one character each, in no particular order.
- `cooldown`: the minimum number of slots between two runs of the same label.

## Output

The minimum total number of slots, idle ones included.

## Examples

### Example 1

<!-- case: ex1 -->

Task A has to run three times with two slots between runs, so it needs at least 7 slots: `A _ _ A _ _ A`. The other tasks fill the gaps: `A B C A B idle A`. One slot stays idle, because there is nothing left to run there.

### Example 2

<!-- case: ex2 -->

With a cooldown of 0, the same task may run in consecutive slots, so no slot is ever idle and the answer is the number of tasks.

## Constraints

- `1 <= tasks.length <= 10^4`
- Every task is an uppercase English letter `A` to `Z`.
- `0 <= cooldown <= 100`

## Follow-ups

- Simulating the processor slot by slot is easy to get right. Can you skip long idle stretches instead of stepping through them?
- Can you compute the answer from the task counts alone, without simulating at all?
- How would you also return one optimal schedule?

## Hints

### Hint 1

Only the number of copies of each label matters, not the order of the input.

### Hint 2

Greedily, in each slot run the available label with the most copies left. The label with the most copies is the one most likely to force idle slots, so it should never wait longer than necessary.

### Hint 3

Let the most frequent label occur `top` times. Its runs split the schedule into `top - 1` frames of `cooldown + 1` slots, followed by a last frame that holds one copy of every label that also occurs `top` times. If the other tasks overflow the frames, no slot is idle at all.
