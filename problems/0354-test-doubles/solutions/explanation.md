# Test Doubles: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rule-lists-timer-heap | optimal | O(r) per call for r rules and expectations; O(c) per spy question over a double's c calls; O(log t) per timer event | O(r + c + t) | default answer; one record per double, one call log and one heap serve all four levels |

Here `r` is the number of rules and expectations of the double called, `c` the number of calls it has received and `t` the number of timers.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Doubles with rules | a map from name to a double; each double has a list of rules per method (pattern, answers, a counter) and a map of `otherwise` answers |
| 2 | Recording | one global log of calls `(name, method, args)`; each double keeps the positions of its own calls in it |
| 3 | Mocks | a mock adds a strict flag, a list of expectations (method, pattern, answer, times, counter) and a list of unexpected calls |
| 4 | A fake clock | the current time, a time on every logged call, a table of timers and a heap of `(due, sequence, id)` |

The early decision that pays off is to route every call, whoever makes it, through one `call` path: the stub answer at level 1, the log entry at level 2, the expectation check at level 3, and a timer at level 4 is just another caller of the same path. A timer that called a double's methods directly would bypass the spy and the mock, and the level 4 cases that check timer calls with `verify` and `callTimes` would fail.

## Approach: rule-lists-timer-heap (Rule lists per method and one call log with a timer heap)

### Intuition

A double is a small lookup machine: given a method and arguments, find the right answer. Keeping the rules per method in the order they were added lets the newest-first search stop at the first fit. Recording is append-only, so one global list gives the order across doubles that `inOrder` needs, and per-double position lists keep `nthCall` and the counts cheap. A mock's expectations are a second, ordered list that is searched before the rules, and whatever falls through all of them is the unexpected call. The fake clock is a discrete-event simulation: a priority queue of due timers, popped in order of time and then of the moment they were queued.

### Algorithm

1. `addStub` and `addMock` put a new double record in the map, unless the name is taken.
2. `onCall` appends a rule `(pattern, answers, used = 0)` to the double's list for the method; `otherwise` sets the method's fallback.
3. `call` appends `(name, method, args, now)` to the log and the log position to the double's list, then answers:
   - for each expectation in order: same method, `used < times` and the pattern fits: increase `used` and return its answer;
   - for each rule of the method from the newest: if the pattern fits, return `answers[min(used, len - 1)]` and increase `used`;
   - if the method has a fallback, return it;
   - a stub returns `""`; a mock appends the call to its unexpected list and returns `"!unexpected"` when strict, `""` when lenient.
4. `callCount`, `matchCount` and `callTimes` walk the double's position list; `nthCall` indexes it from the front or the back.
5. `inOrder` walks the global log once with a pointer to the next step, moving the pointer whenever a call fits that step, and succeeds when the pointer reaches the end.
6. `verify` lists the expectations with `used < times`, then the unexpected calls; `verifyAll` does that for each mock in creation order.
7. `schedule` and `every` store the timer and push `(now + delay, next sequence, id)`. `cancel` marks a waiting timer stopped. `advance` pops while the top is due by the end: skip stopped timers; set the clock to the due time; push a repeating timer back with the next sequence number, or mark a one-shot as done; record `id@due` and make the call. Then the clock moves to the end. `pending` sorts the live heap entries.

### Correctness

Rules: the search runs from the newest rule to the oldest and stops at the first fit, which is the newest rule that fits, as the statement asks. Only the rule that answers moves its counter, so a rule that was shadowed resumes where it left off.

Mocks: the three steps follow the statement's order. An expectation takes a call only while `used < times`, so `used` never passes `times`, and a missing line is printed exactly when the expectation received fewer calls than asked. A call reaches the unexpected list only when no expectation, rule or fallback took it.

`inOrder` is a subsequence test where each step is a predicate on one call. If the calls fit the steps at positions `p1 < p2 < ... < pk`, the greedy walk matches step 1 at some position `q1 <= p1`, and by induction step `i` at some `qi <= pi`, because every call after `q(i-1)` that fits step `i`, including `pi`, is still ahead. So the walk finds a match whenever one exists, and it never claims one that does not, since it only advances on a fitting call.

Timers: the heap orders entries by `(due, sequence)`. The sequence number grows every time an entry is pushed, so among equal due times the entry queued first comes out first, which is the statement's tie rule, including for repeating timers that are queued again when they fire. Each live timer has exactly one entry in the heap, because a repeating timer is pushed again only after its entry has been popped. The loop pops only entries due by the end of the advance, and an entry pushed during the loop with a due time within it is popped in the same loop.

### Complexity

- Time: O(r) per call for r rules and expectations; O(c) per spy question over a double's c calls; O(log t) per timer event — a call checks each expectation and rule of the double at most once; a count or `callTimes` reads the double's call positions; each push and pop of the heap is logarithmic, and a cancelled timer is popped once and dropped.
- Space: O(r + c + t) — each rule, expectation, logged call and timer is stored once, and the heap holds at most one entry per timer.

### Trade-offs

- Rules could be indexed by exact arguments for O(1) lookup, but patterns with `*` need a scan anyway, and doubles in a test have a handful of rules. The linear scan is the honest choice.
- `pending` sorts the heap's live entries on each call. A sorted structure (a balanced tree) would return them in order directly, at a higher cost per insert; tests ask `pending` rarely.
- Lazy cancellation leaves stopped entries in the heap until they reach the top. Removing them eagerly needs a position index into the heap; with few timers per test it is not worth it.

### Pitfalls and edge cases

- A rule that fits but is shadowed by a newer one must not move its counter (hidden case `h1`). A rule's answer list repeats its last entry, not its first.
- A pattern fits only arguments of its own length: `["*"]` does not fit a call without arguments (`h2`).
- `otherwise` is per method and is used only when no rule fits; rules beat it even when they answer `""` (`h3`).
- `nthCall` with `0`, with an index past either end, and on a double with no calls returns `[]` (`h6`).
- `inOrder` needs a distinct call per step: two equal steps need two calls (`ex4`, `h7`).
- Expectations are tried oldest first, not most specific first: a wildcard expectation set first takes the call before a specific one (`h10`).
- A stub rule makes a call allowed on a strict mock, and a call past an expectation's count falls back to the rules before it is unexpected (`h12`).
- `verify` of a stub is `[]` but of an unknown name is `["!unknown"]`; a check must not pass because of a typo (`ex6`).
- A repeating timer goes back in line when it fires, so it loses ties to timers queued earlier (`h14`). Ordering ties by timer id is a common mistake.
- A delay of 0 waits for the next `advance`, and a timer due exactly at the end of an advance fires in it (`h16`). The clock ends at the old time plus `ms` even when nothing fired.
- A timer's call goes through the mock's checks: `h15` has a strict mock that receives unexpected calls from timers.
- Times pass 2^31 in `h18`: they need 64-bit integers.

### Language notes

- Python's `heapq` and Java's `PriorityQueue` order tuples or a comparator on `(due, sequence)`; Kotlin uses `PriorityQueue` with `compareBy`, Go implements `container/heap`'s interface, Rust wraps the tuple `(due, sequence, id)` in `Reverse` inside a `BinaryHeap`, which is a max-heap, and TypeScript, which has no heap, keeps a small binary heap of its own.
- The method `otherwise` and the parameter `strict` are plain names in every language; the method is `onCall` because `when` is a keyword in Kotlin.
- Times are `long` in Java and Kotlin, `int64` in Go and `i64` in Rust. TypeScript numbers hold integers exactly up to 2^53 - 1, well above the largest time.
- Rust keeps the doubles in a `HashMap` plus a `Vec` of names for creation order, because `verifyAll` lists mocks in the order they were made and a `HashMap` has no order. Python's `dict`, TypeScript's `Map` and Java's `LinkedHashMap` keep insertion order; Go keeps a slice of names next to its map.

## Further reading

- G. Meszaros, *xUnit Test Patterns: Refactoring Test Code*, Addison-Wesley, 2007: chapter 11, "Using Test Doubles", and chapter 23, "Test Double Patterns" (Test Stub, Test Spy, Mock Object and Fake Object), the source of the vocabulary used here; the Dummy Object is in chapter 27.
- S. Freeman, N. Pryce, T. Mackinnon and J. Walnes, "Mock Roles, not Objects", Companion to the 19th ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA 2004), pp. 236–246, [doi:10.1145/1028664.1028765](https://doi.org/10.1145/1028664.1028765): mocks as a design tool, the difference between stubbing a call and expecting it, and why to mock only types you own.
