# Check Task Order

## Statement

You have `n` tasks, numbered from `0` to `n - 1`. Some tasks have prerequisites. Each pair `[before, after]` in `prerequisites` says that task `before` must be done earlier than task `after`.

Someone proposes an `order`: the sequence in which they will do the tasks. The order is **valid** when both of these hold:

1. It lists every task exactly once. Nothing is missing and nothing is repeated.
2. For every pair `[before, after]`, task `before` appears earlier in `order` than task `after`.

Return `true` when the order is valid, and `false` otherwise.

## Background

A task's **position** is its place in the proposed order, counting from 0. In the order `[3, 1, 0]`, task 3 has position 0, task 1 has position 1 and task 0 has position 2. Every pair `[before, after]` is an arrow from `before` to `after`, and the order respects the arrow when the position of `before` is smaller than the position of `after`. An order that respects every arrow, and lists each task once, is called a **topological order** of the tasks.

Here is a small example. With tasks 0, 1 and 2 and the pairs `[0, 1]` and `[1, 2]`, the order `[0, 1, 2]` is valid: the positions are 0, 1 and 2, and 0 < 1 and 1 < 2. The order `[1, 0, 2]` is not, because the pair `[0, 1]` needs task 0 to come before task 1, and here task 1 has position 0 while task 0 has position 1.

Some sets of pairs have no valid order at all. Take the pairs `[0, 1]`, `[1, 2]` and `[2, 0]`. They need position(0) < position(1), position(1) < position(2) and position(2) < position(0). Together that says position(0) < position(0), which no position satisfies. A chain of arrows that leads back to where it started is called a **cycle**. When the pairs contain a cycle, every proposed order is invalid, so the answer is `false` whichever order you are given. When they contain no cycle, some order is valid, but a given one may still be wrong.

To decide the answer you therefore need two things: to know whether the order lists each task once, and to know the position of two tasks for each pair. Think about how to get a task's position without searching for it each time.

## Input

- `n`: the number of tasks, numbered `0` to `n - 1`
- `prerequisites`: pairs `[before, after]`, each meaning that task `before` must come earlier than task `after`
- `order`: the proposed order, a list of task numbers. It may be too short, may repeat a task, and may be empty

## Output

`true` if `order` lists every task from `0` to `n - 1` exactly once and puts `before` earlier than `after` for every pair, and `false` otherwise.

## Examples

### Example 1

<!-- case: ex1 -->

The positions are: task 3 at 0, task 1 at 1, task 0 at 2, task 4 at 3 and task 2 at 4. Now check each pair: 3 (position 0) is before 0 (position 2); 3 is before 1 (position 1); 1 (position 1) is before 4 (position 3); 0 (position 2) is before 2 (position 4); and 4 (position 3) is before 2 (position 4). Every pair holds, and every task is listed once.

### Example 2

<!-- case: ex2 -->

The pairs are the same as in Example 1, but one is broken: the pair `[4, 2]` needs task 4 before task 2, and in this order task 2 is at position 3 while task 4 is at position 4. The other four pairs hold, but one broken pair is enough to make the answer `false`.

### Example 3

<!-- case: ex3 -->

The three pairs form a cycle: task 0 must come before 1, task 1 before 2, and task 2 before 0. The order `[0, 1, 2]` satisfies the first two pairs, but task 2 comes after task 0, which the third pair forbids. No order of these three tasks can satisfy all three pairs.

## Constraints

- `1 <= n <= 5000`
- `0 <= prerequisites.length <= 10^4`
- `prerequisites[i].length == 2`
- `0 <= before, after < n` and `before != after`
- No pair appears twice.
- `0 <= order.length <= n` and `0 <= order[i] < n`. A task number may appear more than once.

## Follow-ups

- Can you make the check run in time proportional to `n` plus the number of pairs?
- Instead of `true` or `false`, how would you return the first pair in `prerequisites` that the order breaks?
- Building a valid order yourself, instead of checking one, is the topological sort. Can you see how a check like this one tells you your answer is right?

## Hints

### Hint 1

Take Example 1 and write down the position of each task in the order. Then look at one pair, say `[3, 0]`. How do the two positions tell you whether the pair is respected?

### Hint 2

Before you look at any pair, ask whether the order is a list of every task exactly once. Which kinds of order would fail this, and how could you find out by counting?

### Hint 3

Looking up a task's position by searching the order each time is slow when there are many pairs. Make an array indexed by task number and store each task's position in it once.

### Hint 4

Create `position` with `n` entries, all set to -1. Go through `order`: if the order does not have exactly `n` entries, return `false`; if a task already has a position, it is repeated, so return `false`; otherwise store its index. Then, for every pair `[before, after]`, return `false` if `position[before] >= position[after]`. If nothing failed, return `true`.
