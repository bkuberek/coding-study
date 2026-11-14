# Tally Project (Python)

## Statement

Build a tally that counts amounts per key. Level 1 counts; level 2 takes amounts back out, and from then on several threads share one tally.

## Input

- `Tally()`: creates a tally in which every key counts 0.
- Keys are non-empty strings; amounts are positive.

## Output

Every method returns what its level describes, never an exception.

## Project

The starter holds `tally/tally.py` with the `Tally` class and the methods of level 1. Keep the class in the module `tally.tally`: the grader constructs it from there. Run the tests from the project folder with `.venv/bin/pytest`.

## Level 1: Counts

- `add(key, amount)`: adds `amount` to the count of `key` and returns the new count.
- `count(key)`: returns the count of `key`.

### Example 1

<!-- case: ex1 -->

The count of `a` grows with each call; `b` was never added to.

### Example 2

<!-- case: ex2 -->

Each key counts on its own.

## Level 2: Shared counts

- `take(key, amount)`: removes `amount` from the count of `key` and returns `True`, or returns `False` and changes nothing when the count is lower than `amount`.

From this level on, several threads call one tally at the same time: no call may lose another's change.

### Example 1

<!-- case: ex3 -->

The second take asks for more than is left.

### Example 2

<!-- case: ex4 -->

Nothing can be taken from a key before it is added to.

## Constraints

- At most 1000 operations per case.
- Amounts are from 1 to 10^6.

## Hints

### Hint 1

Every change reads a count and writes it back: what happens when two threads do that at once?
