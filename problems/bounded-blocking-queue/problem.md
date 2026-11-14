# Bounded Blocking Queue

## Statement

Build a first-in, first-out queue of integers with a fixed capacity that several workers use at the same time. Producers add values and consumers remove them; when one side runs ahead, it waits for the other instead of failing.

Implement the class `BoundedBlockingQueue`:

- `BoundedBlockingQueue(capacity)` creates an empty queue that holds at most `capacity` values.
- `put(value)` adds `value` at the back. While the queue is full, it waits until a consumer makes room.
- `take()` removes and returns the value at the front. While the queue is empty, it waits until a producer adds a value.
- `size()` returns how many values the queue holds right now, without waiting.

Reference: this is our own wording of LeetCode problem 1188, [Design Bounded Blocking Queue](https://leetcode.com/problems/design-bounded-blocking-queue/).

## Input

- Constructor `capacity`: the most values the queue may hold at once.
- `put(value)`: the value to add at the back.
- `take()`: no arguments.
- `size()`: no arguments.

Sequential tests are a sequence of calls on one worker: the constructor first, then `put`, `take` and `size` calls in order. Stress tests call the same methods from many workers at once.

## Output

- `put` returns nothing, once the value is in the queue.
- `take` returns the value it removed from the front.
- `size` returns the number of values currently in the queue.

The expected output of a sequential test lists one result per call, with `null` for the constructor and for every `put`.

## Examples

### Example 1

<!-- case: ex1 -->

Two values go in and come out in the order they went in; the size goes from 2 back to 0.

### Example 2

<!-- case: ex2 -->

A queue of capacity 1 must hand each value over before the next one can go in. In a sequential test the calls alternate, so nothing ever waits.

## Constraints

- `1 <= capacity <= 1000`
- `-10^9 <= value <= 10^9`
- Sequential tests never wait: they never take from an empty queue or put into a full one.

## Concurrency

`put`, `take` and `size` are called concurrently by many workers.

- `put` blocks while the queue holds `capacity` values and returns once its value is in the queue. `take` blocks while the queue is empty and returns once it removed a value. Neither may fail or return early because of a spurious wake-up.
- Every value put is taken exactly once: nothing is lost or duplicated.
- Order is first in, first out. In particular, the values of one producer reach the consumers in the order that producer put them.
- `size` never reports a number outside 0 to `capacity`.

Java and Kotlin run on platform threads and on virtual threads, Python and Rust on threads, Go on goroutines, and TypeScript as async workers on one event loop, where `put` and `take` are `async`. In Rust the threads share one queue, so its methods take `&self`. A passing stress run is evidence of thread safety, not proof: a different schedule can still expose a bug.

## Follow-ups

- Can you avoid waking producers when only consumers can make progress, and the other way round?
- How would you add `offer(value, timeoutMs)`, which gives up after a timeout and returns whether it succeeded?
- What changes if a consumer may close the queue, so that waiting producers and consumers must return instead of blocking forever?

## Hints

### Hint 1

A waiting worker must check its condition again after it wakes up: another worker may have changed the queue in between.

### Hint 2

Guard the queue with one lock, and wait on condition variables that release the lock while sleeping: one for "not full" and one for "not empty".

### Hint 3

Counting semaphores fit too: one counts free slots, the other counts stored values, and a mutex protects the queue itself.
