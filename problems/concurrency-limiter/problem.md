# Concurrency Limiter

## Statement

Many workers share a resource that can serve only a few of them at once: a database with a small connection pool, an API with a concurrency quota, a CPU-heavy step that should not run more than `limit` times in parallel. Build the gatekeeper: a counting semaphore that lets at most `limit` workers hold a permit at the same time, and makes the others wait their turn.

Implement the class `ConcurrencyLimiter`:

- `ConcurrencyLimiter(limit)` creates a limiter with `limit` free permits.
- `acquire()` takes a permit. If none is free, it waits until one is released to it. Waiting workers are served first come, first served.
- `tryAcquire()` takes a permit only if one is free right now, and returns whether it did. It never waits.
- `release()` returns a permit. If workers are waiting, the one that has waited longest receives it; otherwise the permit becomes free again.
- `available()` returns the number of free permits right now, without waiting.

Only a worker that holds a permit calls `release`, once per permit it took.

## Input

- Constructor `limit`: the most workers that may hold a permit at the same time.
- `acquire()`, `tryAcquire()`, `release()` and `available()`: no arguments.

Sequential tests are a sequence of calls on one worker: the constructor first, then method calls in order. Stress tests call the same methods from many workers at once.

## Output

- `acquire` and `release` return nothing.
- `tryAcquire` returns `true` when it took a permit and `false` when none was free.
- `available` returns the number of free permits, from 0 to `limit`.

The expected output of a sequential test lists one result per call, with `null` for the constructor, `acquire` and `release`.

## Examples

### Example 1

<!-- case: ex1 -->

With 2 permits, two acquisitions leave none free, so `tryAcquire` fails instead of waiting. Releasing one makes it free again.

### Example 2

<!-- case: ex2 -->

With a single permit, the limiter behaves like a lock that can be tried: the second `tryAcquire` fails until the first holder releases.

## Constraints

- `1 <= limit <= 1000`
- `release` is called only by a worker that holds a permit, so free permits never exceed `limit`.
- Sequential tests never wait: they never call `acquire` while no permit is free.

## Concurrency

`acquire`, `tryAcquire`, `release` and `available` are called concurrently by many workers.

- At no moment do more than `limit` workers hold a permit. Stress tests check this by counting the workers between their `acquire` and their `release`, and they also expect `limit` workers to be inside together at some point, so a limiter that admits only one worker at a time fails.
- `acquire` blocks only while no permit is free, and returns once a releasing worker handed it a permit. No release may be lost: every waiting worker eventually gets a permit.
- Waiting workers are served in the order they started waiting. A permit released while workers wait goes to the first of them, never to a worker that arrives later, and `tryAcquire` never takes a permit ahead of a waiting worker.
- `available` never reports a number outside 0 to `limit`.

Java and Kotlin run on platform threads and on virtual threads, Rust on threads and Go on goroutines, where `acquire` blocks; in Rust the threads share one limiter, so its methods take `&self`. Python and TypeScript run as async workers on one event loop, where `acquire` is `async` and the other methods are plain. A passing stress run is evidence of correct synchronization, not proof; the stress tests check the limit and progress, while first-come, first-served order is part of the contract that they do not observe directly.

## Follow-ups

- How would you add `acquire(timeoutMs)` that gives up after a timeout, without losing a permit that was handed over at the same moment?
- How do you make sure a permit is released when the work in between throws?
- What changes if one call may take several permits at once, without letting small requests starve a large one?

## Hints

### Hint 1

Count the free permits under one lock. The interesting part is what `release` does when someone is waiting.

### Hint 2

If `release` just increments the count and wakes a waiter, a worker that arrives in between can take the permit first. Hand the permit directly to the first waiter instead, without making it free.

### Hint 3

Keep a first-in, first-out queue of waiters. A waiter that was handed a permit does not touch the count again when it wakes up.
