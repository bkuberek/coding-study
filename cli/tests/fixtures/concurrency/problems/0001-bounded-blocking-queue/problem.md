# Bounded Blocking Queue

## Statement

Build a first-in, first-out queue of integers with a fixed capacity that several workers use at the same time. `put` adds a value at the back and waits while the queue is full; `take` removes the value at the front and waits while the queue is empty; `size` reports how many values the queue holds right now.

## Input

- `BoundedBlockingQueue(capacity)`: `capacity` is the most values the queue may hold at once
- `put(value)`: the value to add at the back
- `take()`: no arguments
- `size()`: no arguments

## Output

- `put` returns nothing, once the value is in the queue.
- `take` returns the value it removed from the front.
- `size` returns the number of values currently in the queue.

## Examples

### Example 1

<!-- case: ex1 -->

Two values go in and come out in the order they went in.

### Example 2

<!-- case: ex2 -->

A queue of capacity 1 hands each value over before the next one can go in.

## Constraints

- `1 <= capacity <= 1000`
- `-10^9 <= value <= 10^9`
- Single-threaded examples never wait: they never take from an empty queue or put into a full one.

## Concurrency

`put`, `take` and `size` are called concurrently by many workers. `put` blocks while the queue is full and `take` blocks while it is empty; each returns once the other side made room or a value. Values come out in the order they went in, so values from one producer reach the consumers in that producer's order. `size` never reports a number outside 0 to `capacity`.

Java and Kotlin run on platform and on virtual threads, Python on threads, TypeScript as async workers on one event loop, where `put` and `take` are `async`.

## Hints

### Hint 1

A waiting worker must check its condition again after it wakes up: another worker may have changed the queue in between.
