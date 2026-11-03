# {{title}}

## Statement

TODO: the struct to build over 2 levels as a small Rust project that waits on a clock and whose instance several threads share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every example runs on a virtual clock, so a wait of any length takes no real time. The stress cases run on the real clock and call only methods that wait on no timer.

## Input

- `{{class_name}}::new()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never a panic.

## Project

TODO: what the starter holds. The crate `{{crate_name}}` exports `{{class_name}}` at its root, from `src/lib.rs`, with level 1's methods; keep the crate name and the export, which `cstudy submit` uses. Run the tests from the project folder with `cargo test`; they run on tokio's paused clock, as `cstudy submit` does.

## Level 1: Keep counts

- `add`: TODO; adds `amount` to the count of `key` and returns the new count.
- `count`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for counts

- `wait_for`: TODO; an `async fn` that returns the count of `key` as soon as it is at least `at_least`, or its count once `wait_ms` milliseconds passed without it getting there. From this level a wait runs as a task that shares the instance with the rest of the case, so every method takes `&self`.
- From this level, several threads also call `add` on one instance at the same time, on the real clock. TODO: what must hold under any interleaving, for example that no `add` is lost.

### Example 1

<!-- case: ex2 -->

TODO: what each step does, when the wait ends and why the clock reads what it reads.

## Constraints

- A wait ends at a time the examples fix; no result depends on which of two events due at the same instant comes first.
- TODO: key, amount, wait and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
