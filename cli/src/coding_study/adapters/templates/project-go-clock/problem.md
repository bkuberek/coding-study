# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Go project that waits on a clock, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every case runs on a virtual clock, so a wait of any length takes no real time.

## Input

- `New{{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; absence is `""` for a `string`, never a panic.

## Project

TODO: what the starter holds. `app.go` declares `{{class_name}}`, its constructor `New{{class_name}}` and level 1's methods in the module's root package, where `cstudy submit` imports them from. Run the tests from the project folder with `go test ./...`; they run on the virtual clock, as `cstudy submit` does.

## Level 1: Store values

- `Put(key, value)`: TODO; returns the previous value of `key`, or `""` when there was none.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for values

- `WaitFor(key, waitMs)`: TODO; returns the value of `key` as soon as there is one, or `""` once `waitMs` milliseconds passed without one.

### Example 1

<!-- case: ex2 -->

TODO: what each step does, when the wait ends and why the clock reads what it reads.

## Constraints

- A wait ends at a time the examples fix; no result depends on which of two events due at the same instant comes first.
- TODO: key, value, wait and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
