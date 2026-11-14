# Level Store

## Statement

Build an in-memory key-value store whose API grows one level at a time. Every level adds operations to the same `LevelStore` class, and the operations of earlier levels keep working.

## Input

- `LevelStore()`: creates an empty store.
- Keys and values are strings. Each level's section describes the operations it adds.

## Output

Every operation returns what its level describes. Absence is reported with `""` for strings, never with an exception.

## Level 1: Put and get

- `put(key, value)`: stores `value` under `key`, replacing any earlier value.
- `get(key)`: the value stored under `key`, or `""` when there is none.

### Example 1

<!-- case: ex1 -->

The second `put` replaces the first value of `a`; `b` was never stored.

## Level 2: Remove and size

- `remove(key)`: deletes `key`; returns `true` when it was stored, `false` otherwise.
- `size()`: the number of stored keys.

### Example 1

<!-- case: ex2 -->

Removing `a` a second time finds nothing, and a removed key reads as `""`.

## Level 3: Prefix scans

- `keysWithPrefix(prefix)`: every stored key that starts with `prefix`, in ascending order. The empty prefix matches every key.

### Example 1

<!-- case: ex3 -->

Two keys start with `ap`; none starts with `c`.

## Constraints

- At most 1000 operations per case.
- Keys and values have at most 20 lowercase letters or digits; keys are non-empty.

## Hints

### Hint 1

A hash map answers `put`, `get` and `remove` directly.
