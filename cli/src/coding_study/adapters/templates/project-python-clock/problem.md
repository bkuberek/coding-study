# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Python project that waits on a clock, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every case runs on a virtual clock, so a wait of any length takes no real time.

## Input

- `{{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; absence is `""` for a `str`, never an exception.

## Project

TODO: what the starter holds. `app/main.py` defines `{{class_name}}` with level 1's methods; keep the class in the module `app.main`, where `cstudy submit` imports it from. Run the tests from the project folder with `.venv/bin/pytest`; they run on the virtual clock, as `cstudy submit` does.

## Level 1: Store values

- `put(key, value)`: TODO; returns the previous value of `key`, or `""` when there was none.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for values

- `wait_for(key, wait_ms)`: TODO; an `async def` that returns the value of `key` as soon as there is one, or `""` once `wait_ms` milliseconds passed without one.

### Example 1

<!-- case: ex2 -->

TODO: what each step does, when the wait ends and why the clock reads what it reads.

## Constraints

- A wait ends at a time the examples fix; no result depends on which of two events due at the same instant comes first.
- TODO: key, value, wait and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
