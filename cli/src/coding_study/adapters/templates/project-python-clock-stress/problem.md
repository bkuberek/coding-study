# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Python project that waits on a clock and whose instance several tasks share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every example runs on a virtual clock, so a wait of any length takes no real time. The stress cases run on the real clock and call only methods that wait on no timer.

## Input

- `{{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never an exception.

## Project

TODO: what the starter holds. `app/main.py` defines `{{class_name}}` with level 1's methods; keep the class in the module `app.main`, where `cstudy submit` imports it from. Run the tests from the project folder with `.venv/bin/pytest`; they run on the virtual clock, as `cstudy submit` does.

## Level 1: Keep counts

- `add(key, amount)`: TODO; an `async def` that adds `amount` to the count of `key` and returns the new count.
- `count(key)`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for counts

- `wait_for(key, at_least, wait_ms)`: TODO; an `async def` that returns the count of `key` as soon as it is at least `at_least`, or its count once `wait_ms` milliseconds passed without it getting there.
- From this level, several tasks also call `add` on one instance at the same time, on the real clock. TODO: what must hold under any interleaving, for example that no `add` is lost.

### Example 1

<!-- case: ex2 -->

TODO: what each step does, when the wait ends and why the clock reads what it reads.

## Constraints

- A wait ends at a time the examples fix; no result depends on which of two events due at the same instant comes first.
- TODO: key, amount, wait and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
