# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Python project, written from scratch in your own words (docs/specs/content.md#copyright-policy). Every method takes an explicit `timestamp`; nothing reads a clock.

## Input

- `{{class_name}}()`: TODO
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- Each level's section describes the methods it adds and their other parameters.

## Output

TODO: what each method returns; absence is `""` for a `str`, `-1` for an `int` and `False` for a `bool`, never an exception.

## Project

TODO: what the starter holds. `app/main.py` defines `{{class_name}}` with level 1's methods; keep the class in the module `app.main`, where `cstudy submit` imports it from. Run the tests from the project folder with `.venv/bin/pytest`.

## Level 1: Store values

- `put(timestamp, key, value)`: TODO; returns the previous value of `key`, or `""` when there was none.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Read values

- `get(timestamp, key)`: TODO; returns the value of `key`, or `""` when there is none.

### Example 1

<!-- case: ex2 -->

TODO: what each call does and why it returns that value.

## Constraints

- Timestamps strictly increase across calls.
- TODO: key, value and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
