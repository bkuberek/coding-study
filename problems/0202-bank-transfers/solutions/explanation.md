# Bank Transfers: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| global-lock | brute | O(1) per transfer, O(n) per total | O(n) | low contention, or as the obviously correct baseline |
| ordered-locks | optimal | O(1) per transfer, O(n) per total | O(n) | default answer; transfers between unrelated accounts run in parallel |

Both make each transfer one atomic step. They differ in lock granularity: one lock for everything, or one lock per account, which brings the classic deadlock and its classic cure, a global lock order.

## Approach: global-lock (One lock for the whole bank)

### Intuition

If every method runs under the same lock, the bank behaves exactly like a sequential program: no two operations ever overlap, so no update can be lost and no total can see money in flight.

### Algorithm

1. Keep the balances in an array and one mutex.
2. `transfer`: reject missing accounts; under the mutex, reject when the source holds less than `amount`, otherwise subtract from the source and add to the destination.
3. `balance` and `total`: read under the mutex.

### Correctness

All reads and writes of the array happen under one mutex, so the operations are linearizable in the order they take the mutex. A transfer's check and both updates run without interruption, so the sum of the balances is the same before and after every transfer, and `total` always observes a state between two transfers.

### Complexity

- Time: O(1) per transfer, O(n) per total — a transfer does constant work; `total` adds up n balances.
- Space: O(n) — one balance per account.

### Trade-offs

It is simple and cannot deadlock, because there is only one lock. It also serializes every transfer: on many cores, unrelated transfers wait for each other, and a long `total` blocks the whole bank. In an interview it is the right first answer, followed by "now make transfers between different accounts run in parallel".

### Pitfalls and edge cases

- `balance` and `total` need the lock too: on the JVM an unguarded read may see a stale or, for a `long` on 32-bit platforms, a torn value; and `total` without the lock sees half-done transfers.
- A transfer to the same account must still check the balance and must not change it.

### Language notes

- Java: `synchronized` methods on the bank; on JDK 21 a virtual thread inside `synchronized` pins its carrier, which is correct but limits parallelism.
- Kotlin: `ReentrantLock.withLock { }`, which does not pin virtual threads. With coroutines the same design is one `Mutex` with `withLock`, whose waiting suspends instead of blocking.
- Python: one `threading.Lock`. The GIL alone does not make `check, subtract, add` one step, so the lock is required.
- Go: one `sync.Mutex` with `defer b.mu.Unlock()` in every method.
- Rust: a `Mutex<Vec<i64>>`; the guard is the only way to reach the balances, so no method can forget the lock. The threads share the bank, so the methods take `&self`.

## Approach: ordered-locks (One lock per account taken in index order)

### Intuition

A transfer conflicts only with operations on its own two accounts, so each account gets its own lock and a transfer holds both of its accounts' locks. Taking two locks opens the door to deadlock: transfer A to B holds A and waits for B, while transfer B to A holds B and waits for A. The cure is to take locks in one global order, here by account number, so that a cycle of waiting transfers cannot form.

### Algorithm

1. Keep the balances and one lock per account.
2. `transfer`: reject missing accounts. Let `first` be the smaller and `second` the larger account number; lock `first`, then `second`. Under both, reject when the source holds less than `amount`, otherwise move the money. Unlock in reverse order.
3. A transfer to the same account takes that one lock and only checks the balance (the JVM references simply lock the same reentrant lock twice).
4. `balance`: lock that account and read it.
5. `total`: lock every account in index order, add up the balances, then unlock them all.

### Correctness

Atomicity: while a transfer holds the locks of both accounts, no other operation can read or write them, so its check and both updates form one step and the sum of the balances never changes.

Consistency of `total`: once `total` holds every lock, no transfer is in progress, so it adds up a state in which every transfer either fully happened or did not start.

Deadlock freedom: every operation acquires locks in increasing account order. Suppose some workers waited for each other in a cycle. Each one waits for a lock with a larger number than every lock it holds, so following the cycle the lock numbers would strictly increase all the way back to the start, which is impossible. Hence no cycle, and every operation eventually gets its locks.

### Complexity

- Time: O(1) per transfer, O(n) per total — a transfer takes two locks and does constant work; `total` takes n locks and adds up n balances.
- Space: O(n) — one balance and one lock per account.

### Trade-offs

Transfers between disjoint pairs of accounts run fully in parallel, which is what a bank with many accounts needs. The cost is more locks, the discipline of the global order in every code path, and an expensive `total` that briefly stops every transfer. Real systems avoid that stop with a snapshot (multi-version data or a write-ahead log) and avoid lock ordering across machines with a single-writer design per account, or with transactions that abort and retry.

Ordering by `System.identityHashCode` or object address is the textbook alternative when there is no natural key; it needs a tie-breaker lock for the rare equal hashes.

### Pitfalls and edge cases

- Ordering must be by a global key (the account number), never by argument position: `transfer(a, b)` and `transfer(b, a)` must lock in the same order.
- A transfer to the same account would take the same lock twice: fine with a reentrant lock, a self-deadlock with Python's non-reentrant `threading.Lock`, which is why the Python reference handles it first.
- `total` must use the same order as transfers, or it can deadlock with them.
- Unlock every lock on every path, including the early `return false`; `try`/`finally`, `withLock` and `with` do that.

### Language notes

- Java: an array of `ReentrantLock`, with nested `try`/`finally` blocks. Virtual threads park on `ReentrantLock` without pinning their carrier, unlike `synchronized` on JDK 21. `tryLock` with a timeout is the alternative cure for deadlock: back off and retry instead of ordering.
- Kotlin: the same JDK locks with nested `withLock { }`, which unlock on every path. With coroutines, one `Mutex` per account works the same way; ordering matters just as much, because a suspended coroutine holding a `Mutex` blocks others exactly like a thread. Coroutines are not autograded here.
- Python: a list of `threading.Lock`, nested `with` blocks for the two accounts, and `contextlib.ExitStack` to hold every lock in `total`. Under the GIL only one thread runs Python code at a time, but a thread can be switched out between taking its first and its second lock, so the deadlock is real.
- Go: a slice of `sync.Mutex` and `defer` for each unlock. A `sync.Mutex` is not reentrant, so a transfer from an account to itself must lock it once; locking it twice blocks the goroutine forever, where Java's `ReentrantLock` would just count the second lock.
- Rust: a `Vec<Mutex<i64>>`, so each balance is reachable only through its own guard. A transfer to the same account locks it once, since a `Mutex` locked twice on one thread never returns; for two accounts it locks the lower index first and then sorts the two guards into source and target. `total` collects every guard before it reads any balance.

## Broken: no-lock (Balances without a lock)

### Bug

Balances are read and written without any mutual exclusion. Two transfers out of the same account both read the old balance and both write back their own result, so one withdrawal is lost and money is created; an auditor adding up the balances between a transfer's withdrawal and its deposit sees money in flight. The stress test catches it through the auditor's `total` (`bounds`) and through the final balances, whose `sum` no longer equals the starting total.

In Go the balances are a plain `[]int64` that goroutines read and write at once. Safe Rust has no unsynchronized `i64` to share, so its version makes each balance an `AtomicI64`: every load and store is atomic, but the transfer loads, checks and stores in separate steps, which loses updates exactly the same way.

### Failing interleaving

1. Account 0 holds 100. Teller A reads it for a transfer of 30 and is switched out.
2. Teller B reads 100 for a transfer of 50 and writes 50.
3. Teller A resumes and writes 100 - 30 = 70 over B's update.
4. Both destinations were credited, so 50 was created: the total is now 50 too high.

### Fix

Make the check and both updates one atomic step under the locks of both accounts, and have `total` take every lock, as in the `ordered-locks` (or `global-lock`) approach.

## Broken: argument-order (Locks taken in argument order)

### Bug

The transfer locks `fromAccount` first and `toAccount` second. Two transfers in opposite directions between the same accounts take the same two locks in opposite orders, so each can end up holding one lock while waiting for the other. Neither can ever continue: a deadlock, which the stress test reports as `STALLED` when its deadline passes. Go and Rust deadlock the same way: a goroutine waiting in `sync.Mutex.Lock` and a thread waiting in `Mutex::lock` cannot be interrupted, so the runner asks for a restart after the stall.

### Failing interleaving

1. Worker A runs `transfer(0, 1, 1)` and locks account 0.
2. Worker B runs `transfer(1, 0, 1)` and locks account 1.
3. A tries to lock account 1 and waits for B.
4. B tries to lock account 0 and waits for A. Both wait forever.

### Fix

Take the two locks in a global order, the smaller account number first, regardless of the direction of the transfer, as in the `ordered-locks` approach.
