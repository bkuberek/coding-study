# Read-Write Lock: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| monitor | optimal | O(1) per op | O(waiters) | default answer; the same design underlies library read-write locks |

The whole lock is a little state machine: a count of active readers, a flag for an active writer, and a count of waiting writers. Every transition happens under one mutex, and workers wait on conditions until their transition is allowed.

## Approach: monitor (Counters and conditions under one lock)

### Intuition

Readers conflict only with writers, and writers conflict with everyone. So a reader needs to know whether a writer is active, and a writer needs to know whether anyone is active. To keep writers from starving, readers must also know whether a writer is waiting: if so, they queue up behind it instead of extending the current read phase forever.

### Algorithm

1. State, guarded by one mutex: `readers` (active readers), `writing` (a writer is active), `waitingWriters`.
2. `acquireRead`: while `writing` or `waitingWriters > 0`, wait on the "readable" condition; then increment `readers`.
3. `releaseRead`: decrement `readers`; if it reached 0, signal one waiting writer.
4. `acquireWrite`: increment `waitingWriters`; while `writing` or `readers > 0`, wait on the "writable" condition; then decrement `waitingWriters` and set `writing`.
5. `releaseWrite`: clear `writing`; if writers wait, signal one of them, otherwise wake every waiting reader.
6. `tryAcquireRead` and `tryAcquireWrite` test the same conditions once, without waiting.

The TypeScript reference runs the same state machine, but hands the lock over at release time: `releaseWrite` sets `writing` (or increments `readers` for every admitted reader) before it resolves the waiters' promises, so a woken worker never needs to check again.

### Correctness

Invariant: `writing` implies `readers == 0`, and at most one writer is active. A writer sets `writing` only after observing `!writing && readers == 0` under the mutex, and a reader increments `readers` only after observing `!writing` under the mutex; no other transition can happen in between, so both halves of the invariant hold. The `while` loops make the check and the transition one atomic step, even after a spurious wake-up or when several waiters wake at once.

Progress: whenever the lock becomes free for a waiting worker, someone is woken. The last reader to leave signals a writer; a leaving writer signals the next writer or all readers. A waiting writer blocks new readers, so the set of active readers can only shrink until the writer gets in: writers cannot starve because of readers.

### Complexity

- Time: O(1) per op — each operation does constant work under the mutex besides waiting; waking k waiting readers costs O(k) once, which is paid by those readers' acquisitions.
- Space: O(waiters) — the counters are O(1), and the condition queues (or the TypeScript resolver lists) hold one entry per waiting worker.

### Trade-offs

Writer preference protects writers but can starve readers when writers arrive faster than they finish. Reader preference (readers enter whenever no writer is active) is simpler and maximizes read throughput, but starves writers under a steady read load, which is usually worse, because writers then make no progress at all. Fair, phase-alternating locks bound both waits at the cost of more state.

A read-write lock only pays off when read sections are long or reads vastly outnumber writes; for short critical sections its bookkeeping is slower than a plain mutex, and on the JVM a `StampedLock` with optimistic reads is faster still for read-mostly data.

### Pitfalls and edge cases

- Signalling only one waiter with a single shared condition can wake a reader when only a writer may proceed; use two conditions, or `notifyAll` with `while` loops.
- `releaseWrite` must wake all waiting readers, not one, or the remaining readers sleep although they may enter.
- A writer that is interrupted (or cancelled) while waiting must undo its `waitingWriters` increment and wake the readers it was holding back.
- Read holds are not owned by a thread here; library locks such as `ReentrantReadWriteLock` require the releasing thread to be the acquiring one, and support reentrancy, which this lock does not.

### Language notes

- Java: `ReentrantLock` with two `Condition`s, `readable` and `writable`. Virtual threads park on `Condition.await` without pinning their carrier; `synchronized` with `wait` pins it on JDK 21. The library versions are `ReentrantReadWriteLock` (reentrant, optionally fair) and `StampedLock` (not reentrant, with optimistic reads).
- Kotlin: the same JDK classes with `lock.withLock { }`, plus the `ReentrantReadWriteLock.read { }` and `write { }` extension functions. Coroutines have no read-write mutex in `kotlinx.coroutines`; the usual design is the same state machine guarded by a `Mutex`, with waiting lists of `CompletableDeferred`, so that waiting suspends instead of blocking a thread. Coroutines are not autograded here.
- Python: two `threading.Condition` objects sharing one `threading.Lock`. The GIL does not make the check of `self._writing` and the update of `self._readers` one atomic step, so the mutex is still needed; the standard library has no read-write lock.
- TypeScript: one event loop, so the counters need no mutex, but every `await` is a point where other workers run. The reference keeps FIFO lists of waiting readers and writers and updates the state when it admits them, which avoids re-checking after a wake-up.
- Go: a `sync.Mutex` and two `sync.Cond`s on it, waited on in `for` loops. `sync.RWMutex` is the library version; it also gives waiting writers priority over new readers, and like this design it may be unlocked by a different goroutine than the one that locked it.
- Rust: the counters in a `Mutex` with two `Condvar`s. `std::sync::RwLock` hands out guards that must be dropped by the code that took them, so it cannot implement `acquireRead` and `releaseRead` as separate calls; its fairness also depends on the operating system. The threads share the lock, so the methods take `&self`.

## Broken: unlocked-count (Reader count without a lock)

### Bug

Writers exclude each other with a mutex, but readers only spin while `writing` is set and then increment a shared counter, all without the mutex. A reader's check and its increment are two steps, and a writer's check of the counter and its `writing = true` are two more, so a writer and a reader can both get in (`section` violation). On the JVM, `volatile` makes the fields visible but does not make `readers++` atomic: concurrent increments and decrements are lost, so the count drifts, letting a writer in among readers or locking writers out forever (`STALLED`, or the final `tryAcquireWrite` returning `false`).

The Go version keeps the flag and the counter in plain fields that goroutines read and write at once, with a `sync.Mutex` between writers; `readers++` is a load and a store, so it loses updates as on the JVM. Safe Rust has no plain field to share, so its version keeps them in an `AtomicBool` and an `AtomicI32` and, like `volatile`, makes each load and store atomic but not the increment: it loads the count and stores the count plus one in a separate step. Its writers exclude each other with a compare-and-swap on another `AtomicBool`.

### Failing interleaving

1. Reader R checks `writing`: false. Before R increments `readers`, it is switched out.
2. Writer W takes the writer mutex, sees `readers == 0`, sets `writing` and enters.
3. R resumes, increments `readers` and enters the section that W holds.

### Fix

Make the check and the update one atomic step under the same mutex the writer uses, and wait on a condition instead of spinning, as in the `monitor` approach.

## Broken: if-not-while (Writer wait guarded by if)

### Bug

`releaseWrite` and the last `releaseRead` wake every waiting worker. Readers re-check their condition, but a woken writer continues past its `if` and sets `writing` without looking again. When two writers wait, one release lets both in (`section` violation with two exclusive holders). Go's version waits on one `sync.Cond` and wakes with `Broadcast`; Rust's waits on one `Condvar` and wakes with `notify_all`, and a `Condvar` may also wake a writer spuriously, with nobody's release at all.

### Failing interleaving

1. Writer A holds the lock; writers B and C wait.
2. A releases and wakes everyone.
3. B re-acquires the mutex first, sets `writing` and enters.
4. C re-acquires the mutex, does not re-check, sets `writing` again and enters the section that B holds.

### Fix

Wait in a `while` loop that re-checks `writing || readers > 0` after every wake-up, as in the `monitor` approach.
