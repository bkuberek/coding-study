# Concurrency Limiter: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| hand-off | optimal | O(1) per op | O(waiters) | default interview answer; shows the wake-up logic explicitly |
| fair-semaphore | optimal | O(1) per op | O(waiters) | production JVM code, or when the interviewer allows library primitives |

Both keep a count of free permits and a first-in, first-out queue of waiting workers. The hand-off version writes the queue by hand; the fair semaphore is the same design inside the JDK.

## Approach: hand-off (FIFO waiter queue with direct hand-off)

### Intuition

A counting semaphore is a counter of free permits plus a queue of workers waiting for one. The subtle part is `release` while someone waits. If it just makes the permit free and wakes a waiter, a worker that arrives before the waiter runs again sees a free permit and takes it: the waiter was overtaken, and if it does not re-check, two workers now hold the same permit. Handing the permit directly to the first waiter closes that gap: the permit never becomes free, so nobody else can take it.

### Algorithm

1. State: `permits`, the number of free permits (starts at `limit`), and `waiters`, a FIFO queue. All of it is guarded by one lock (threads) or touched only between `await` points (async).
2. `acquire`: if `permits > 0`, decrement it and return. Otherwise append a fresh waiter to the queue and wait until that waiter is marked as granted.
3. `tryAcquire`: if `permits > 0`, decrement it and return `true`; otherwise return `false`.
4. `release`: if the queue is empty, increment `permits`. Otherwise remove the first waiter, mark it granted and wake exactly that waiter. `permits` stays unchanged: the permit moved from the releasing worker to the waiter.
5. `available`: return `permits`.

### Correctness

Invariant: `permits` plus the number of holders (workers that returned from `acquire` or a successful `tryAcquire`, or that were granted while still waking up) equals `limit`. Every operation preserves it: taking a free permit moves one from `permits` to a holder, a hand-off moves one from a holder to a holder, and a release with an empty queue moves one back to `permits`. So there are never more than `limit` holders, and `permits` stays within 0 to `limit`.

Waiters exist only while `permits == 0`: a worker queues only when no permit is free, and a release with waiters never increments `permits`. Therefore `acquire` and `tryAcquire` can never take a permit ahead of a waiter, and waiters are served in queue order. No wake-up is lost: the grant is recorded in the waiter before it is woken, and the waiter loops on that flag, so a spurious wake-up or a late wake-up still finds the right answer.

### Complexity

- Time: O(1) per op — queue operations at the ends and a constant number of counter updates.
- Space: O(waiters) — one queue entry per worker that is waiting.

### Trade-offs

Direct hand-off gives strict FIFO fairness and makes barging impossible, at the cost of a context switch for every contended permit: the permit cannot go to a thread that is already running. Unfair semaphores (the JDK default) let a running thread barge in, which gives higher throughput under contention but can starve a waiter. A single condition with `notifyAll` is simpler to write but wakes every waiter on each release, and is correct only with a `while` re-check.

### Pitfalls and edge cases

- A waiter must not decrement `permits` after it wakes up: the hand-off already accounted for it.
- Cancellation and interruption: a waiter that is interrupted after it was granted holds a permit that nobody will release. The references pass it on to the next waiter (or back to the pool); a waiter interrupted before it was granted removes itself from the queue.
- `release` without a matching acquisition would grow `permits` beyond `limit`; the contract forbids it, and `java.util.concurrent.Semaphore` would silently allow it.
- With `limit` 1 the limiter is a mutex with a FIFO queue, which is the hardest schedule for hand-off logic.

### Language notes

- Java: one `ReentrantLock`, and one `Condition` per waiter so that `release` wakes exactly the granted worker (`signal`, not `signalAll`). On JDK 21, virtual threads park on `Condition.await` without pinning their carrier; `synchronized` with `wait` would pin it, which is still correct but wastes carrier threads when many virtual threads wait.
- Kotlin: the same JDK classes with `lock.withLock { }`, which is inline, so `return` inside it returns from `acquire`. With coroutines the same design is `kotlinx.coroutines.sync.Semaphore(limit)`, which suspends instead of blocking and is FIFO; coroutines are not autograded here.
- Python: the async model, where only an `await` can let another worker run, so no lock is needed. Each waiter is an `asyncio.Future`; `release` resolves the first one that is not already cancelled. A task cancelled after its future was resolved passes the permit on in its `except CancelledError` branch. `asyncio.Semaphore` is the library version and is FIFO since Python 3.11.1. In the threads model the same design needs a `threading.Lock` and one `threading.Condition` (or `Event`) per waiter.
- TypeScript: one event loop and the async model: each waiter is the `resolve` function of a pending promise, kept in a FIFO array. Calling `resolve` does not run the waiter immediately; its continuation is queued, which is exactly why the permit must be handed over rather than made free.

## Approach: fair-semaphore (Fair semaphore from the standard library)

### Intuition

`java.util.concurrent.Semaphore` is a counting semaphore with an optional fairness policy. Constructed with `fair = true`, it queues waiting threads in arrival order and grants permits in that order, which is exactly this limiter.

### Algorithm

1. Create `new Semaphore(limit, true)`.
2. `acquire` calls `acquire()`; `release` calls `release()`; `available` returns `availablePermits()`.
3. `tryAcquire` calls `tryAcquire(0, TimeUnit.SECONDS)`: unlike the no-argument `tryAcquire()`, the timed form honors the fairness setting and fails while other threads are queued.

### Correctness

The JDK semaphore keeps the permit count in an atomic state of an `AbstractQueuedSynchronizer` and parks waiting threads in its FIFO queue. In fair mode, an acquisition succeeds only when the count is positive and no thread is queued ahead of it, so no more than `limit` permits are out at once and waiters are served in order.

### Complexity

- Time: O(1) per op — one compare-and-set on the count in the uncontended case; queue operations at the ends otherwise.
- Space: O(waiters) — one queue node per waiting thread.

### Trade-offs

It is the code to write in production and shows that you know the library. In an interview it usually leads to the follow-up "now implement it yourself", which is the hand-off approach. Fair mode costs throughput under contention, because a running thread cannot take a just-released permit.

### Pitfalls and edge cases

- `tryAcquire()` without arguments barges even on a fair semaphore; use the timed form for FIFO fairness.
- `release()` never checks that the caller holds a permit; an extra release silently raises the count above `limit`.
- `acquire()` throws `InterruptedException`; `acquireUninterruptibly()` exists for callers that cannot handle it.

### Language notes

- Java: `Semaphore(limit, true)`; virtual threads park on it without pinning their carrier.
- Kotlin: the same JDK class; `tryAcquire(0, TimeUnit.SECONDS)` needs no `try`, because Kotlin has no checked exceptions. For coroutines, `kotlinx.coroutines.sync.Semaphore` with `withPermit { }` is the equivalent.
- Python and TypeScript have no reference for this approach: Python's `asyncio.Semaphore` does not expose its free count publicly, and TypeScript has no built-in semaphore.

## Broken: if-not-while (Wait guarded by if)

### Bug

`release` increments the count and wakes every waiter (`notifyAll`, `signalAll`, or resolving every pending promise). Each woken waiter continues past its `if` and decrements the count without checking it again, so several waiters take the one released permit. More than `limit` workers are inside at once (`section` with `max_occupancy`, or an exclusive violation with limit 1), and the count goes negative (`bounds` on `available`).

### Failing interleaving

1. The limit is 3; three workers hold permits, and workers D and E wait.
2. Holder A releases: the count becomes 1, and both D and E are woken.
3. D re-acquires the lock, decrements the count to 0 and enters.
4. E re-acquires the lock, does not re-check, decrements the count to -1 and enters: four holders.

### Fix

Re-check the condition in a `while` loop after every wake-up, or better, hand the permit to exactly one waiter as in the `hand-off` approach.

## Broken: no-hand-off (Release without a waiter hand-off)

### Bug

`release` makes the permit free and wakes the first waiter. In asyncio, `Future.set_result` only schedules the waiter's wake-up for a later turn of the event loop, and in the meantime the releasing worker keeps running: it calls `acquire` again, finds a free permit and takes it. The woken waiter then decrements the count as well, so two workers hold one permit (`section`), and the count drops below zero.

The same bug exists in TypeScript, but the stress tests cannot expose it there, so this reference is Python only. A resolved promise resumes its waiter at the next microtask checkpoint, and the harness awaits between two calls of a worker, so the waiter always runs before the releasing worker's next `acquire`. In application code that calls `release()` and then `acquire()` in one synchronous run, the newcomer still barges in.

### Failing interleaving

1. The limit is 1; worker A holds the permit and worker B waits.
2. A calls `release`: the count becomes 1 and B's future gets its result, but B only runs on a later turn of the loop.
3. A continues without suspending, calls `acquire` again, sees a free permit and takes it: the count is 0.
4. B resumes, decrements the count to -1 and enters the section that A is in.

### Fix

When workers wait, give the released permit to the first of them without making it free, and let the woken waiter return without touching the count, as in the `hand-off` approach.
