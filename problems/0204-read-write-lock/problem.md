# Read-Write Lock

## Statement

A plain mutex lets one worker in at a time, even when every worker only reads. A read-write lock is smarter: any number of readers may hold it together, because reading does not change anything, but a writer needs it alone. Build one that also keeps writers from starving: once a writer is waiting, readers that arrive after it wait too.

Implement the class `ReadWriteLock`:

- `ReadWriteLock()` creates a lock that nobody holds.
- `acquireRead()` takes the lock for reading. It waits while a writer holds the lock or while a writer is waiting for it.
- `releaseRead()` gives back one read hold.
- `acquireWrite()` takes the lock for writing. It waits while anyone, reader or writer, holds the lock.
- `releaseWrite()` gives back the write hold.
- `tryAcquireRead()` takes a read hold only if `acquireRead` would not have to wait right now, and returns whether it did.
- `tryAcquireWrite()` takes the write hold only if nobody holds the lock right now, and returns whether it did.

A worker calls `releaseRead` only while it holds a read hold, and `releaseWrite` only while it holds the write hold.

## Input

- Constructor: no arguments.
- Every method: no arguments.

Sequential tests are a sequence of calls on one worker: the constructor first, then method calls in order. Stress tests call the same methods from many workers at once.

## Output

- `acquireRead`, `releaseRead`, `acquireWrite` and `releaseWrite` return nothing.
- `tryAcquireRead` and `tryAcquireWrite` return `true` when they took the lock and `false` otherwise.

The expected output of a sequential test lists one result per call, with `null` for the constructor and for every method that returns nothing.

## Examples

### Example 1

<!-- case: ex1 -->

Two read holds coexist, so the second read attempt succeeds while a write attempt fails. Once both readers released, a writer gets in.

### Example 2

<!-- case: ex2 -->

While a writer holds the lock, neither readers nor another writer may enter. After the writer releases, a reader gets in.

## Constraints

- Releases always match an earlier successful acquisition of the same kind.
- At most 64 workers use one lock.
- Sequential tests never wait: they never call `acquireRead` or `acquireWrite` when the call would have to wait.

## Concurrency

Every method is called concurrently by many workers.

- Mutual exclusion: while a writer holds the lock, no other writer and no reader holds it. Readers may hold it together, and must be able to: stress tests expect at least two readers inside at the same time at some point, so a lock that admits one worker at a time fails.
- `acquireRead` and `acquireWrite` block only as long as the rules above require, and return once they hold the lock. No release may be lost: when the lock becomes free, a waiting worker gets in.
- Writer preference: while a writer waits, newly arriving readers wait as well, so a stream of overlapping readers cannot keep a writer out forever. Among waiting writers the order is not specified.
- Stress tests count the workers between each acquisition and its release (shared for readers, exclusive for writers), and after every run check that the lock is free again.

Java and Kotlin run on platform threads and on virtual threads, Python on threads, and TypeScript as async workers on one event loop, where `acquireRead` and `acquireWrite` are `async` and the other methods are plain. A passing stress run is evidence of correct synchronization, not proof; writer preference is part of the contract, but the stress tests check mutual exclusion and progress, not starvation.

## Follow-ups

- With writer preference, a steady stream of writers starves the readers instead. How would you serve readers and writers in alternating phases?
- How would you let the writer downgrade to a read hold without letting another writer in between?
- Why is read-to-write upgrading deadlock-prone when two readers try it at once?

## Hints

### Hint 1

Keep three numbers under one mutex: active readers, whether a writer is active, and how many writers wait.

### Hint 2

A reader may enter when no writer is active and none is waiting. A writer may enter when no reader and no writer is active. Wait in a `while` loop for those conditions.

### Hint 3

Wake writers when the last reader leaves, and when a writer leaves wake the next writer if one waits, otherwise every waiting reader.
