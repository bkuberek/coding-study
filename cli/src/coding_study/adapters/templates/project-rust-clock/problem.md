# {{title}}

## Statement

TODO: the struct to build over 2 levels as a small Rust project that waits on a clock, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every case runs on tokio's paused clock, so a wait of any length takes no real time.

## Input

- `{{class_name}}::new()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; absence is `""` for a `String`, never a panic.

## Project

TODO: what the starter holds. The crate `{{crate_name}}` exports `{{class_name}}` at its root, from `src/lib.rs`, with level 1's methods; keep the crate name and the export, which `cstudy submit` uses. Run the tests from the project folder with `cargo test`; they run on tokio's paused clock, as `cstudy submit` does.

## Level 1: Store values

- `put`: TODO; returns the previous value of `key`, or `""` when there was none.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for values

- `wait_for`: TODO; an `async fn` that returns the value of `key` as soon as there is one, or `""` once `wait_ms` milliseconds passed without one. From this level a wait runs as a task that shares the instance with the rest of the case, so every method takes `&self`.

### Example 1

<!-- case: ex2 -->

TODO: what each step does, when the wait ends and why the clock reads what it reads.

## Constraints

- A wait ends at a time the examples fix; no result depends on which of two events due at the same instant comes first.
- TODO: key, value, wait and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
