# Token Bucket Limiter: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| locked | optimal | O(1) per op | O(1) | default answer in every language |
| cas-state | optimal | O(1) per op, amortized under contention | O(1) | JVM code on a hot path where lock hand-offs cost too much |

Both compute the refill lazily from the elapsed time and make "refill, check, take" one atomic step: under a lock, or as one compare-and-set of an immutable state.

## Approach: locked (Lazy refill and take under one lock)

### Intuition

The bucket's state is two numbers: the tokens it holds and the latest timestamp it refilled to. Nothing needs to happen between calls; each call catches up on the elapsed time first. The race to prevent is that two workers read the same state and both act on it, so one lock covers the whole read-refill-decide-write sequence.

### Algorithm

1. State: `stored` (starts at `capacity`) and `lastRefill` (starts at 0), guarded by one lock.
2. Refill to `t`: if `t > lastRefill`, set `stored = min(capacity, stored + (t - lastRefill) * refillPerSecond)` and `lastRefill = t`; otherwise do nothing.
3. `tryAcquire(t, n)`: under the lock, refill to `t`; if `stored < n` return `false`; otherwise subtract `n` and return `true`.
4. `available(t)`: under the lock, refill to `t` and return `stored`.

### Correctness

Under the lock the calls happen one at a time, in lock order, so the bucket behaves exactly like the sequential definition. `lastRefill` only grows, and each refill adds tokens for the interval since the previous refill, so the intervals never overlap: the same seconds are never paid out twice. A take happens only after a check against the value it changes, in the same critical section, so `stored` never goes below zero and a grant is always covered.

Conservation follows: as long as the cap is not hit, the refills add up to `refillPerSecond * (latest timestamp)`, and every token leaves the bucket only through a granted request. This is the identity the stress test checks.

### Complexity

- Time: O(1) per op — constant arithmetic under one lock.
- Space: O(1) — two numbers and a lock.

### Trade-offs

It is short, obviously correct and fast enough for nearly every service: an uncontended lock costs tens of nanoseconds. Under very high contention every request serializes on one lock, which is where the compare-and-set version or a sharded design (one bucket per core or per client, with a share of the rate each) helps. A background thread that adds tokens on a timer is the other common design; it costs a thread, and its timing jitter makes counts inexact.

### Pitfalls and edge cases

- An out-of-order timestamp must not move `lastRefill` backwards, or the next caller is paid again for seconds already counted.
- Cap at `capacity` before storing; a long idle period must not allow a burst larger than the bucket.
- A request larger than what is stored takes nothing; partial grants change the semantics.
- `(t - lastRefill) * refillPerSecond` can overflow a 32-bit integer; use `long` on the JVM.

### Language notes

- Java: a `ReentrantLock` with `try`/`finally`, which does not pin virtual threads, unlike `synchronized` on JDK 21. The fields need no `volatile`: the lock's acquire and release order every access.
- Kotlin: the same JDK lock with `withLock { }`. A coroutine version would guard the same two fields with a `kotlinx.coroutines.sync.Mutex`, or confine the bucket to one coroutine that serves requests from a `Channel`; coroutines are not autograded here.
- Python: one `threading.Lock`. Each line of the refill is atomic under the GIL, but the sequence of lines is not: a thread can be switched out between updating `_stored` and `_last_refill`, so the lock is required.
- Go: one `sync.Mutex` with `defer b.mu.Unlock()`; the refill is a helper that runs with the mutex held.
- Rust: the two fields in a `Mutex`, and a refill helper that takes the guard's `&mut` state, so it can only run with the lock held. The threads share the bucket, so the methods take `&self`.

## Approach: cas-state (Compare-and-set on an immutable state)

### Intuition

Put both numbers in one immutable object held by an atomic reference. A worker reads the current state, computes the next state (refilled, then taken), and installs it with a single compare-and-set. If another worker changed the state in between, the compare-and-set fails and the worker retries from the new state, so no update is ever based on a stale read.

### Algorithm

1. State: an `AtomicReference` to an immutable `(stored, lastRefill)` pair, initially `(capacity, 0)`.
2. `tryAcquire(t, n)`: loop: read `current`; compute `refilled` from it as in the locked version; the next state is `refilled` minus `n` tokens if it holds at least `n`, otherwise `refilled` itself. If the next state is `current` (nothing changed), return at once; otherwise try to replace `current` with it, and on failure loop.
3. `available(t)`: the same loop with "refill only" as the next state, returning its stored tokens.

### Correctness

Every successful compare-and-set replaces exactly the state the new one was computed from, so the successful updates form a chain, each a valid sequential step: the linearization order is the order of successful compare-and-sets, and a call that changed nothing is linearized at its read. A failed attempt writes nothing and retries from fresh state, so no update is based on a stale read.

Denials and `available` must publish their refill too. Skipping it looks harmless, since the next caller would compute the same tokens, but `lastRefill` is part of the observable state: after `available(10)`, a call with timestamp 5 must add nothing, which only holds if timestamp 10 was recorded.

### Complexity

- Time: O(1) per op, amortized under contention — one read, a little arithmetic and one compare-and-set; a failed compare-and-set means another worker made progress, so retries are bounded by the other workers' successes.
- Space: O(1) — one state object at a time, plus short-lived garbage per attempt.

### Trade-offs

No thread ever blocks, so a preempted worker cannot hold everyone up, and uncontended calls avoid lock overhead. Under heavy contention many attempts fail and retry, burning CPU, and every attempt allocates a state object. It also only works because the whole state fits in one reference; anything larger becomes hard to reason about. Python has no compare-and-set for objects, so this approach has no Python reference.

### Pitfalls and edge cases

- Both numbers must change together: two separate atomics (`AtomicLong` for tokens, another for the timestamp) bring back the double refill, because no single operation updates both.
- Compare-and-set on the reference compares identity, so build a new state object for every change and never mutate one.
- A read-only `available` that computes the refill without installing it returns the right number once, but leaves `lastRefill` behind, so a later call with an earlier timestamp is paid again.
- Packing both values into one `long` avoids the allocation but limits their ranges.

### Language notes

- Java: a private `record State(long stored, long lastRefill)` in an `AtomicReference<State>`. The same pattern works on virtual threads, which never park in it.
- Kotlin: a private class in an `AtomicReference`; `atomicfu` or `kotlin.concurrent.atomics` offer the same compare-and-set. In coroutines, a lock-free state like this needs no `Mutex` at all, since the compare-and-set loop never suspends.
- Python has no reference for this approach: the standard library has no compare-and-set on object references.
- Go and Rust have no reference for this approach. Go would keep a pointer to an immutable state in an `atomic.Pointer[state]` and loop on `CompareAndSwap`; Rust's standard library has no safe atomic swap of a heap value (`AtomicPtr` leaves freeing the replaced state to the caller), so the two fields would be packed into one `AtomicU64`, or kept behind a `Mutex`, which is the `locked` approach.

## Broken: no-lock (Refill and take without a lock)

### Bug

Nothing is synchronized. Two workers that refill at about the same time both read the old `lastRefill` and both add the tokens for the same seconds; on the JVM, concurrent `stored -= tokens` updates also overwrite each other. Either way the bucket grants more than it earned, which breaks the `conserved` check: granted plus remaining exceeds capacity plus refills.

In Go the fields are plain `int64`s that goroutines read and write at once. Safe Rust has no unsynchronized field to share, so its version keeps `stored` and `lastRefill` in two `AtomicI64`s: each load and store is atomic, but the refill and the take are still separate loads and stores, and they lose updates the same way.

### Failing interleaving

1. The bucket holds 0 tokens and refilled to second 41 at the latest.
2. Worker A calls `tryAcquire(42, 1)`, sets `stored` to 1 for the elapsed second, and is switched out before it records `lastRefill = 42`.
3. Worker B calls `tryAcquire(42, 1)`, still sees `lastRefill = 41`, adds the same second again and takes a token.
4. A resumes, records `lastRefill = 42` and takes a token too: two tokens were granted for one second of refill.

### Fix

Hold one lock across the refill, the check and the take, as in the `locked` approach, or replace the whole state with one compare-and-set, as in `cas-state`.

## Broken: unlocked-refill (Refill outside the lock)

### Bug

The take is locked, but the refill runs before the lock is taken, on the reasoning that it "only does arithmetic on time". It still reads and writes `stored` and `lastRefill`, so refills race with each other (counting the same seconds twice) and with the locked take (a refill computed from a stale `stored` overwrites a take that happened in between, giving the tokens back). `volatile` makes the fields visible across threads, but does not make the read-compute-write sequence atomic. The `conserved` check fails.

The Go version refills plain fields before `TryAcquire` locks its mutex. The Rust version has the same shape with atomics in place of `volatile`: the fields are `AtomicI64`s that the refill loads and stores outside the mutex, while the take loads, checks and stores them inside it.

### Failing interleaving

1. The bucket holds 3 tokens and refilled to second 9.
2. Worker A calls `tryAcquire(10, 1)`, reads `stored = 3` in its refill and is switched out before it writes 4.
3. Worker B calls `tryAcquire(9, 1)`: no refill, then it takes a token under the lock, leaving 2.
4. A resumes, writes `stored = 4` from its stale read, then takes its token under the lock: 3 tokens are left although only 4 were ever available and 2 were taken. B's token came back for free.

### Fix

Move the refill inside the critical section, so that refill, check and take are one atomic step, as in the `locked` approach.
