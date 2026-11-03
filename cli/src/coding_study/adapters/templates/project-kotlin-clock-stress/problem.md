# {{title}}

## Statement

TODO: the class to build over 2 levels as a small Kotlin project that waits on a clock and whose instance several threads share from level 2, written from scratch in your own words (docs/specs/content.md#copyright-policy). Nothing here reads the real clock: every example runs on a virtual clock, so a wait of any length takes no real time. The stress cases run on the real clock and call only methods that wait on no timer.

## Input

- `{{class_name}}()`: TODO
- Each level's section describes the methods it adds and their parameters.

## Output

TODO: what each method returns; a key that was never added counts `0`, never an exception.

## Project

TODO: what the starter holds. `src/main/kotlin/app/{{class_name}}.kt` defines the class `app.{{class_name}}` with level 1's methods; keep the class there, where `cstudy submit` loads it from. Run the tests from the project folder with `../../jvm/gradlew test`; they run on the virtual clock of `kotlinx-coroutines-test`, as `cstudy submit` does.

## Level 1: Keep counts

- `add(key, amount)`: TODO; adds `amount` to the count of `key` and returns the new count.
- `count(key)`: TODO; returns the count of `key`, or `0` when nothing was added to it.

### Example 1

<!-- case: ex1 -->

TODO: what each call does and why it returns that value.

## Level 2: Wait for counts

- `waitFor(key, atLeast, waitMs)`: TODO; a `suspend fun` that returns the count of `key` as soon as it is at least `atLeast`, or its count once `waitMs` milliseconds passed without it getting there.
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
