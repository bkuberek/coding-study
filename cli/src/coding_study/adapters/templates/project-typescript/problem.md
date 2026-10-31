# {{title}}

## Statement

TODO: the class to build over 2 levels as a small TypeScript project, written from scratch in your own words (docs/specs/content.md#copyright-policy). Every method takes an explicit `timestamp`; nothing reads a clock.

## Input

- `new {{class_name}}()`: TODO
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- Each level's section describes the methods it adds and their other parameters.

## Output

TODO: what each method returns; absence is `""` for a `string`, `-1` for a `number` and `false` for a `boolean`, never an exception.

## Project

TODO: what the starter holds. `src/main.ts` exports `{{class_name}}` by name with level 1's methods; keep the class in that file, where `cstudy submit` imports it from. Run the tests from the project folder with `node --test`.

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
