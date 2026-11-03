# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Java project whose instance several threads share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads a clock.

## Input

- `new {{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never an exception.

## Project

TODO: what the starter holds. `src/main/java/app/{{class_name}}.java` defines the class `app.{{class_name}}` with level 1's methods; keep the class there, where `cstudy submit` loads it from. Run the tests from the project folder with `../../jvm/gradlew test`.

## Level 1: Keep counts

- `add(key, amount)`: TODO; adds `amount` to the count of `key` and returns the new count.
- `count(key)`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Share the counts

- `take(key, amount)`: TODO; removes `amount` from the count of `key` and returns `true`, or returns `false` and changes nothing when the count is lower.
- From this level, several threads call the methods on one instance at the same time. TODO: what must hold under any interleaving, for example that no `add` is lost and no count goes below zero.

### Example 1

<!-- case: ex2 -->

TODO: what each call does and why it returns that value.

## Constraints

- TODO: key, amount and call-count ranges

## Hints

### Hint 1

TODO: the most general nudge first.
