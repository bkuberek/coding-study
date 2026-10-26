# Debug: Mutable Default Argument: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| none-sentinel | optimal | O(n) | O(n) | default answer: `None` as the default, a fresh list per top-level call |

## Approach: none-sentinel (None sentinel for the accumulator)

### Intuition

Python evaluates a default value once, when the `def` statement runs, and stores that object on the function (`leaf_values.__defaults__`). `leaves: list[int] = []` therefore creates one list when the module loads, and every call that omits `leaves` receives that same list. The recursion appends to it and returns it, so the first top-level call is correct. The second call starts from a list that already holds the first call's leaves, the third from one holding both, and so on, for as long as the process lives. CI calls the function once, so CI passes. The service, and this problem's test runner, reuse one process, so every call after the first leaks.

The fix: default to `None`, a sentinel that is never mutated, and create a new list inside the function when the caller passed none. Recursive calls still pass the list down explicitly, so they share it, as they should.

### Debugging approach

1. **Reproduce the order dependence.** Call the function on Example 2's tree in a fresh interpreter: the result is right. Call it on Example 1's tree first, then on Example 2's: the second result is wrong. A result that depends on what ran before means hidden state that survives between calls.
2. **Minimize.** `leaf_values(tree_a)` followed by `leaf_values(tree_b)` in one REPL session is the whole bug. The second result is `leaves(a) + leaves(b)`.
3. **Find the state.** Nothing global is visibly assigned, so look for objects that outlive a call: module globals, class attributes, caches and default values. `leaf_values.__defaults__` shows the list growing after each call.
4. **Fix and test the fix with two calls.** A test that calls once cannot catch this, so the regression test must call the function at least twice.

### Algorithm

1. If `leaves` is `None`, this is a top-level call: set `leaves` to a new empty list.
2. If `root` is `None`, return `leaves`.
3. If `root` has no children, append `root.val`.
4. Recurse into `root.left`, then `root.right`, passing the same `leaves`.
5. Return `leaves`.

### Correctness

Each top-level call (no `leaves` argument) creates its own list, so no state survives between calls. Within one call, the recursion is a preorder walk that visits the left subtree before the right. Leaves are therefore appended in left-to-right order, and every leaf exactly once, since each node is visited once. Only nodes with no children are appended. The empty tree returns the fresh empty list.

### Complexity

- Time: O(n) — every node is visited once, and each append is amortized O(1).
- Space: O(n) — the output list holds up to about n/2 leaves, and the recursion stack is O(h), which is at most n.

### Trade-offs

The `None` sentinel is the minimal fix and keeps the signature. A nested helper (`def walk(node)` closing over a local `leaves`) removes the optional parameter from the public API, which is cleaner because callers can no longer pass a list by accident. Returning `leaf_values(left) + leaf_values(right)` needs no accumulator at all, but copies lists at every level, O(n·h) in total. An iterative walk with an explicit stack avoids Python's recursion limit (about 1000 frames by default) for very deep trees.

### Pitfalls and edge cases

- The general trap: a mutable default value (list, dict, set, or any object) is shared by every call that does not pass the argument. Immutable defaults (`None`, numbers, strings, tuples) are safe.
- `leaves = leaves or []` is wrong. An empty list is falsy, so a recursive call that receives the caller's empty list builds a new one, appends to it, and the caller never sees it. On Example 1 it returns `[]`.
- `if not leaves:` has the same flaw. Test identity: `if leaves is None:`.
- With the bug, the returned list *is* the default object, so a caller that modifies the result (for example, sorts or clears it) also changes what the next call starts from. After the fix each call returns its own list.

### Prevention

- Linters catch it: Ruff and flake8-bugbear rule `B006` (mutable argument default), and Pylint `W0102` (`dangerous-default-value`). Type checkers do not, because `list[int] = []` is well typed.
- Test functions with hidden state by calling them more than once in one test, and run tests in a single process with randomized order, for example with `pytest-randomly`.
- Prefer APIs without accumulator parameters; keep accumulators in a private helper.

### Language notes

- Python only. TypeScript, Java and Kotlin evaluate default arguments at every call (Java has none), so `leaves: number[] = []` in TypeScript or `leaves: MutableList<Int> = mutableListOf()` in Kotlin creates a new list per call.
- The same evaluate-once rule applies to `dataclasses.field` defaults, which is why dataclasses reject `= []` and require `default_factory=list`.
