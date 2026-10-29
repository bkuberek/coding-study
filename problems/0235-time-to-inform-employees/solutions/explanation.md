# Time to Inform All Employees: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| walk-up | brute | O(n * h) | O(1) | the hierarchy is shallow, or as a correctness oracle |
| top-down | optimal | O(n) | O(n) | default answer |

Here `h` is the height of the hierarchy. The generator makes it about n / 2 up to n = 4000, so the measured class of `walk-up` on the ladder is `n^2`.

## Approach: walk-up (Walk up from every employee to the head)

### Intuition

An employee hears the news only after every manager above them has passed it on, one after another. So the moment an employee hears it is the sum of `informTime` over their chain of managers. The answer is the largest such sum.

### Algorithm

1. For each employee, start with `elapsed = 0` and follow `manager` upward.
2. At each step, move to the manager and add that manager's `informTime`.
3. Stop at the head, and keep the maximum `elapsed` over all employees.

### Correctness

The hearing time of an employee equals the sum of the inform times along the chain of managers from the head down to the employee's own manager, because each manager spends exactly their `informTime` before their reports hear it and the reports of a manager all hear it at the same moment. The walk adds exactly these terms, and the answer is the latest hearing time.

### Complexity

- Time: O(n * h) — `n` walks of at most `h` steps each, which is quadratic for a long chain.
- Space: O(1) — a few counters.

### Trade-offs

No extra memory and almost no code, but it re-adds the same prefix sums for employees that share managers. Memoizing the hearing time per employee would make it linear; the top-down traversal gets the same effect without a table.

### Pitfalls and edge cases

- Add the manager's time, not the employee's own: an employee's own `informTime` delays their reports, not themselves.
- The head alone gives 0, since the loop never runs.

### Language notes

- All four languages: a `while (current != headID)` loop on primitive arrays; no allocation.
- The parameter `headID` is `head_id` in Python and stays `headID` in the other languages.

## Approach: top-down (Traverse down from the head carrying the elapsed time)

### Intuition

The hearing time of a report is the hearing time of its manager plus the manager's `informTime`. Start at the head with 0 and carry that value down the hierarchy, taking the maximum.

### Algorithm

1. Build the list of direct reports of every manager from the `manager` array, skipping `-1`.
2. Put `(headID, 0)` on a stack.
3. Pop an `(employee, heardAt)`, update the maximum with `heardAt`, and push each of the employee's reports with `heardAt + informTime[employee]`.
4. Return the maximum.

### Correctness

By induction from the head down: the head hears at 0, and if an employee is pushed with their correct hearing time, each report is pushed with that time plus the employee's `informTime`, which is the report's hearing time. The hierarchy is a tree, so each employee is pushed exactly once, and the maximum over all of them is the answer.

### Complexity

- Time: O(n) — building the report lists and visiting each employee once.
- Space: O(n) — the report lists and the stack.

### Trade-offs

Iterative, so the 2000 levels of the constraint do not matter for the stack depth. A memoized walk-up is the other linear solution; the top-down version is simpler to explain.

### Pitfalls and edge cases

- Skip `-1` when building the report lists, or the head is added to a list at index `-1`.
- Employees without reports have `informTime` 0, so they pass the elapsed time on unchanged, to nobody.

### Language notes

- Python: lists of lists and a stack of tuples.
- TypeScript: `Array.from({ length: n }, () => [])` builds independent lists (not `new Array(n).fill([])`, which shares one list).
- Java: a `List<List<Integer>>` and an `ArrayDeque<int[]>` holding `{employee, heardAt}` pairs.
- Kotlin: `Array(n) { mutableListOf<Int>() }` and a `Pair<Int, Int>` stack. Answers stay within `Int`: at most 2000 * 1000.
