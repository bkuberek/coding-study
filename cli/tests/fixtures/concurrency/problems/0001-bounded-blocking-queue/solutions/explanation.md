# Bounded Blocking Queue: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| monitor | optimal | O(1) per op | O(capacity) | default answer |

## Approach: monitor (One lock with two conditions)

### Intuition

One lock protects the deque. Producers wait on a "not full" condition and consumers on a "not empty" condition, so each side sleeps until the other side changes the queue.

### Algorithm

1. `put`: take the lock; while the deque is at capacity, wait on "not full"; append; signal "not empty".
2. `take`: take the lock; while the deque is empty, wait on "not empty"; remove the front; signal "not full".
3. `size`: take the lock and read the length.

### Correctness

Every read and write of the deque happens under the one lock, so operations are atomic. A worker leaves its wait loop only when its condition holds while it holds the lock, so no put overfills the deque and no take removes from an empty one.

### Complexity

- Time: O(1) per op — each operation does constant work besides waiting.
- Space: O(capacity) — the deque never holds more than `capacity` values.

### Trade-offs

Two conditions wake only the side that can make progress; one condition with `notifyAll` is simpler but wakes every waiter on each change.

### Pitfalls and edge cases

Waiting under `if` instead of `while` breaks as soon as two workers wait on the same condition: the second one wakes to a state that the first one already changed.

### Language notes

Java uses `ReentrantLock` with two `Condition`s; on JDK 21 virtual threads park on them without pinning a carrier. Kotlin uses the same JDK classes with `withLock`; with coroutines the same design is a `Mutex` with a `Channel` or two `Semaphore`s. Python uses `threading.Condition` objects that share one lock; the GIL does not make the check-then-act sequence atomic. TypeScript keeps FIFO queues of pending resolvers: an `await` is the only place another worker can run.

## Broken: no-lock (Deque without a lock)

### Bug

The deque is shared with no mutual exclusion: workers spin until the size looks right, then mutate. Two consumers can both see one element and both remove it, which loses or duplicates values (`equal_multisets`, `distinct`) or throws from an empty deque (`ERROR`).

### Failing interleaving

1. The queue holds one value.
2. Consumer A sees a non-empty deque and is switched out.
3. Consumer B sees the same value and removes it.
4. Consumer A resumes and removes from the now empty deque.

### Fix

Guard every access with one lock and wait on conditions instead of spinning, as in the `monitor` approach.

## Broken: if-not-while (Wait guarded by if)

### Bug

A woken worker does not check its condition again. With several consumers waiting, one value wakes more than one of them; the second removes from an empty deque (`ERROR`, or `INVALID` in TypeScript).

### Failing interleaving

1. Consumers A and B wait on an empty queue.
2. A producer adds one value and wakes both.
3. A removes the value.
4. B continues past its `if` and removes from the empty deque.

### Fix

Wait in a `while` loop that re-checks the condition after every wake-up, as in the `monitor` approach.
