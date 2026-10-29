# Bounded Blocking Queue: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| monitor | optimal | O(1) per op | O(capacity) | default interview answer; one lock, explicit wait conditions |
| semaphores | optimal | O(1) per op | O(capacity) | the counting view reads more naturally, or the language has fast semaphores |

Both approaches keep one deque under mutual exclusion. They differ in how a worker waits: on a condition variable that it re-checks, or on a semaphore whose count already is the condition.

## Approach: monitor (One lock with two conditions)

### Intuition

One lock protects the deque. Producers wait on a "not full" condition and consumers on a "not empty" condition, so each side sleeps until the other side changes the queue. Waiting on a condition releases the lock, which lets the other side in to make that change.

### Algorithm

1. `put`: take the lock; while the deque holds `capacity` values, wait on "not full"; append the value; signal "not empty"; release the lock.
2. `take`: take the lock; while the deque is empty, wait on "not empty"; remove the front value; signal "not full"; release the lock and return the value.
3. `size`: take the lock and read the length.

### Correctness

Every read and write of the deque happens under the one lock, so each operation is atomic and the deque behaves exactly like a sequential FIFO queue. A worker leaves its wait loop only when it holds the lock and its condition is true, so no `put` overfills the deque and no `take` removes from an empty one, even after a spurious wake-up or after another worker got there first.

No wake-up is lost: a worker checks its condition and goes to sleep while holding the lock, and the change that makes the condition true also happens under the lock, followed by a signal. Each `put` signals "not empty" once, which is enough because it added exactly one value that exactly one taker can consume; the same holds for `take` and "not full".

### Complexity

- Time: O(1) per op — each operation does constant work besides waiting for the lock or a condition.
- Space: O(capacity) — the deque never holds more than `capacity` values.

### Trade-offs

Two conditions wake only the side that can make progress. One condition with `notifyAll` is simpler, and the only option with Java's built-in `synchronized`/`wait`, but every change then wakes every waiter, and all but one go back to sleep. `signal` (one waiter) is safe here only because the two kinds of waiters wait on different conditions; with one shared condition, `notify` can wake a producer when only a consumer could proceed, and the queue stalls.

Compared with semaphores, the monitor states the condition explicitly (`size == capacity`), which is easier to extend: closing the queue or adding a timeout is one more check in the loop.

### Pitfalls and edge cases

- Waiting under `if` instead of `while` breaks as soon as two workers wait on the same condition: the second one wakes to a state that the first one already changed.
- Signalling before changing the deque, or outside the lock, opens a window where the woken worker re-checks too early and sleeps again with no further signal coming.
- `size` must take the lock too; on the JVM an unguarded read may see a stale value.
- Capacity 1 turns every operation into a hand-off between one producer and one consumer, which is the hardest schedule for wake-up logic.

### Language notes

- Java: `ReentrantLock` with two `Condition`s; `await` releases the lock and re-acquires it before returning. On JDK 21, virtual threads park on `Condition.await` without pinning their carrier thread, whereas `synchronized` with `Object.wait` pins it (still correct, only slower). `java.util.concurrent.ArrayBlockingQueue` is the production version of exactly this design.
- Kotlin: the same JDK classes, with `lock.withLock { ... }` releasing the lock on every path. With coroutines the same design is a `Mutex` plus waiting lists of `CompletableDeferred`, or simply `Channel(capacity)`, whose `send` and `receive` suspend instead of blocking; coroutines are not autograded here.
- Python: two `threading.Condition` objects that share one `threading.Lock`. The GIL makes single bytecode operations atomic, not the check-then-act sequence of `put` and `take`, so the lock is still required. `queue.Queue(maxsize)` is the standard library version.
- TypeScript: there are no threads, but every `await` is a point where another worker runs. The reference keeps FIFO lists of pending resolvers for takers and putters and hands values over directly: `put` resolves a waiting taker with its value instead of storing it, and `take` admits a waiting putter's value into the slot it just freed. Because the hand-off happens synchronously, no other worker can slip in between.
- Go: a `sync.Mutex` and two `sync.Cond`s built on it with `sync.NewCond(&q.mu)`, over a ring buffer of `capacity` slots. `Cond.Wait` unlocks, sleeps and locks again, and its documentation asks for the `for` loop, since it may return before the condition holds. A buffered channel, `make(chan int, capacity)`, is the built-in version of this whole queue.
- Rust: a `Mutex<VecDeque<i32>>` and two `Condvar`s. `wait` takes the guard and hands it back locked, and spurious wake-ups are allowed, so it sits in a `while` loop; `Condvar::wait_while` is that loop built in. The worker threads share the queue, so `put` and `take` take `&self`.

## Approach: semaphores (Two counting semaphores and a mutex)

### Intuition

Count instead of checking: one semaphore counts free slots and starts at `capacity`, the other counts stored values and starts at 0. A producer first claims a free slot, a consumer first claims a stored value; the mutex only protects the deque during the actual append or removal.

### Algorithm

1. `put`: acquire a free slot (blocks while there is none); under the mutex, append the value; release one stored value.
2. `take`: acquire a stored value (blocks while there is none); under the mutex, remove the front value; release one free slot; return the value.
3. `size`: read the length under the mutex.

### Correctness

Invariant: free slots plus stored values plus operations in flight equals `capacity`, and the "stored" count never exceeds the number of values in the deque. A `take` that acquired a stored value is therefore guaranteed to find one, and a `put` that acquired a free slot is guaranteed that the deque has room. The mutex makes each append and removal atomic, so the deque stays a FIFO queue. Semaphores remember releases, so a release that happens before the matching acquire is not lost.

### Complexity

- Time: O(1) per op — two semaphore operations and one constant-time deque operation.
- Space: O(capacity) — at most `capacity` values are stored.

### Trade-offs

It needs no wait loop, so the `if`-versus-`while` bug cannot happen. It uses three synchronizers instead of one lock, and extensions such as closing the queue are harder, because a semaphore cannot be woken with "stop waiting". In Python the `threading.Semaphore` is itself a condition variable with a lock inside, so this version is slower than the monitor there.

### Pitfalls and edge cases

- The order matters: acquire the semaphore before the mutex. Taking the mutex first and then blocking on the semaphore holds the mutex while sleeping, so the other side can never make progress: a deadlock.
- Release the counterpart semaphore only after the deque changed, or a consumer may acquire "stored" and find the deque still empty.
- `size` reads the deque, not a semaphore count: the counts lag behind the deque while operations are in flight.

### Language notes

- Java: `java.util.concurrent.Semaphore` for the counts and `synchronized` on a private object for the deque. Virtual threads park on `Semaphore.acquire` without pinning.
- Kotlin: the same JDK `Semaphore`; `synchronized(mutex) { }` is a standard library function. With coroutines, `kotlinx.coroutines.sync.Semaphore` and `Mutex` give the same shape with suspending `acquire` and `lock`.
- Python: `threading.Semaphore` and `threading.Lock`; `threading.BoundedSemaphore` would additionally catch a release beyond the initial count.
- TypeScript has no built-in semaphore, so this approach has no TypeScript reference; the monitor's resolver lists are the async equivalent.
- Go: buffered channels are Go's counting semaphores. `free` starts with `capacity` tokens and `stored` with none; receiving a token is the acquire, which blocks while the channel is empty, and sending one back is the release. A `sync.Mutex` guards the ring buffer.
- Rust's standard library has no semaphore, so this approach has no Rust reference; a `Mutex` with `Condvar`s is the `monitor` approach.

## Broken: no-lock (Deque without a lock)

### Bug

The deque is shared with no mutual exclusion: workers spin until the size looks right, then mutate. Two consumers can both see one element and both remove it, which loses or duplicates values (`equal_multisets`, `distinct`) or throws from an empty deque (`ERROR`). On the JVM a missing lock also means a missing memory barrier: the JIT may hoist the size read out of the spin loop, so a worker spins forever (`STALLED`).

### Failing interleaving

1. The queue holds one value.
2. Consumer A sees a non-empty deque and is switched out before removing.
3. Consumer B sees the same value and removes it.
4. Consumer A resumes and removes from the now empty deque: `IndexError` in Python, `null` unboxed to `int` on the JVM.

The Go version keeps its values in a fixed ring buffer with atomic `head` and `tail` counters, so no count is lost, and spins on their difference. But the check and the claim are separate steps, and a producer moves `tail` before it writes the slot: two consumers both see the last value and both claim a slot, so one reads a slot nobody filled, and a consumer can read a slot before its producer wrote it (`equal_multisets`, `distinct`, `source_order`). It never grows a slice without a lock, because Go is not memory-safe under a data race: a slice header torn between two goroutines can send a write outside its array. Safe Rust cannot express this bug at all; its broken reference is `if-not-while`.

### Fix

Guard every access with one lock and wait on conditions instead of spinning, as in the `monitor` approach.

## Broken: if-not-while (Wait guarded by if)

### Bug

A woken worker does not check its condition again. With several consumers waiting, one value wakes more than one of them through `notifyAll`; the second removes from an empty deque (`ERROR`, or `INVALID` in TypeScript, where `shift()` returns `undefined`).

### Failing interleaving

1. Consumers A and B wait on an empty queue of capacity 1.
2. A producer adds one value and wakes both.
3. A re-acquires the lock first and removes the value.
4. B re-acquires the lock, continues past its `if` and removes from the empty deque.

In Go the same bug is `if` around `sync.Cond.Wait` with `Broadcast`, and the second `take` panics with an index out of range. In Rust it is `if` around `Condvar::wait` with `notify_all`, and `pop_front().unwrap()` panics on the empty deque; a `Condvar` may also wake up spuriously, which breaks an `if` even with a single waiter.

### Fix

Wait in a `while` loop that re-checks the condition after every wake-up, as in the `monitor` approach.
