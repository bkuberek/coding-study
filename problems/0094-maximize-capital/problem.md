# Maximize Capital

## Statement

A small company wants to grow its capital before going public. It starts with capital `w` and may complete at most `k` projects, one after another. Project `i` can only be started when the current capital is at least `capital[i]`; completing it adds its pure profit `profits[i]` to the capital. Starting a project does not use up any capital: the requirement is only a minimum balance, and the profit is added on completion. Each project can be completed at most once.

Choose the projects, and their order, to make the final capital as large as possible, and return that final capital.

Reference: this is our own wording of LeetCode problem 502, [IPO](https://leetcode.com/problems/ipo/).

## Input

- `k`: the maximum number of projects to complete.
- `w`: the starting capital.
- `profits`: the profit of each project.
- `capital`: the minimum capital needed to start each project; `capital[i]` belongs to `profits[i]`.

## Output

The largest capital reachable after completing at most `k` projects.

## Examples

### Example 1

<!-- case: ex1 -->

With capital 1, projects 0 (needs 1, earns 5) and 1 (needs 0, earns 2) are affordable. Taking project 0 raises the capital to 6, which unlocks project 2 (needs 6, earns 8). The second pick takes it: 6 + 8 = 14.

### Example 2

<!-- case: ex2 -->

Starting from nothing, only project 1 is affordable. Its profit of 1 unlocks project 0, whose profit of 4 brings the capital to 5 and unlocks project 2: 0 + 1 + 4 + 7 = 12.

## Constraints

- `1 <= k <= 10^5`
- `0 <= w <= 10^9`
- `1 <= profits.length == capital.length <= 10^5`
- `0 <= profits[i] <= 10^4`
- `0 <= capital[i] <= 10^9`
- The answer fits in a 32-bit signed integer.

## Follow-ups

- Is it ever better to pick an affordable project with a smaller profit first? Argue why not.
- Scanning all projects in every round is O(k n). Which two orderings of the projects do you need, and which structure serves each?
- How does the algorithm change if completing a project also costs its capital requirement?

## Hints

### Hint 1

Capital never decreases, so a project that is affordable now stays affordable forever. Among the affordable projects, which one should you take?

### Hint 2

Always take the affordable project with the largest profit: it leaves you with at least as much capital as any other choice, and therefore with at least as many options afterwards.

### Hint 3

Sort the projects by required capital. Walk through them with a pointer, pushing the profit of every newly affordable project into a max-heap, and pop the heap once per round.
