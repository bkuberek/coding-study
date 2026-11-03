# {{title}}

## Statement

TODO: the struct to build over 2 levels as a small Rust project whose instance several threads share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads a clock.

## Input

- `{{class_name}}::new()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never a panic.

## Project

TODO: what the starter holds. The crate `{{crate_name}}` exports `{{class_name}}` at its root, from `src/lib.rs`, with level 1's methods; keep the crate name and the export, which `cstudy submit` uses. Run the tests from the project folder with `cargo test`.

## Level 1: Keep counts

- `add`: TODO; adds `amount` to the count of `key` and returns the new count.
- `count`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Share the counts

- `take`: TODO; removes `amount` from the count of `key` and returns `true`, or returns `false` and changes nothing when the count is lower.
- From this level, several threads call the methods on one instance at the same time, so every method takes `&self` and the struct keeps its state behind a lock (`std::sync::Mutex`). TODO: what must hold under any interleaving, for example that no `add` is lost and no count goes below zero.

### Example 1

<!-- case: ex2 -->

TODO: what each call does and why it returns that value.

## Constraints

- TODO: key, amount and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
