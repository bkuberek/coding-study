# {{title}}

## Statement

TODO: the type to build over 2 levels as a small Go project whose instance several goroutines share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads a clock.

## Input

- `New{{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never a panic.

## Project

TODO: what the starter holds. `app.go` declares `{{class_name}}`, its constructor `New{{class_name}}` and level 1's methods in the module's root package, where `cstudy submit` imports them from. Run the tests from the project folder with `go test ./...`.

## Level 1: Keep counts

- `Add(key, amount)`: TODO; adds `amount` to the count of `key` and returns the new count.
- `Count(key)`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Share the counts

- `Take(key, amount)`: TODO; removes `amount` from the count of `key` and returns `true`, or returns `false` and changes nothing when the count is lower.
- From this level, several goroutines call the methods on one instance at the same time. TODO: what must hold under any interleaving, for example that no `add` is lost and no count goes below zero.

### Example 1

<!-- case: ex2 -->

TODO: what each call does and why it returns that value.

## Constraints

- TODO: key, amount and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
