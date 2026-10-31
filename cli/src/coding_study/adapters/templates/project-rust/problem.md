# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Rust project, written from scratch in your own words (docs/specs/content.md#copyright-policy). Every method takes an explicit `timestamp`; nothing reads a clock.

## Input

- `{{class_name}}::new()`: TODO
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- Each level's section describes the methods it adds and their other parameters.

## Output

TODO: what each method returns; absence is `""` for a `String`, `-1` for an `i64` and `false` for a `bool`, never a panic.

## Project

TODO: what the starter holds. The crate `{{crate_name}}` exports `{{class_name}}` at its root, from `src/lib.rs`, with level 1's methods; keep the crate name and the export, which `cstudy submit` uses. Run the tests from the project folder with `cargo test`.

## Level 1: Store values

- `put(&mut self, timestamp: i64, key: String, value: String) -> String`: TODO; returns the previous value of `key`, or `""` when there was none.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Read values

- `get(&mut self, timestamp: i64, key: String) -> String`: TODO; returns the value of `key`, or `""` when there is none.

### Example 1

<!-- case: ex2 -->

TODO: what each call does and why it returns that value.

## Constraints

- Timestamps strictly increase across calls.
- TODO: key, value and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
