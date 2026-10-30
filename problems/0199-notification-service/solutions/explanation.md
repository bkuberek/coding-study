# Notification Service: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| channel-pipeline | optimal | O(b) per send to render; O(log r) per scheduled retry | O(u + d + r) | default answer; each concern is one small class and `send` is a short pipeline |

Here `b` is the length of the template body, `r` the number of pending retries, `u` the number of contacts and `d` the number of delivered messages.

## Approach: channel-pipeline (Channel strategies with a rate-limit and retry pipeline)

### Intuition

A notification goes through the same steps on every channel: is the channel switched on for this user, may we send now (rate limit), what does the message look like here (format), and did it go through (delivery, or a retry later). Only the formatting differs per channel, so that is the one method behind the channel interface; everything else is shared code that never asks which channel it is handling. Adding a channel is then a registration, not a change to `send`.

Retries are the only behavior that is not triggered by a call. Because time is a parameter, they become a min-heap of attempts ordered by due time, drained at the start of every call that knows the time. Each retry is judged at its own due time, so the result is the same as if a real scheduler had run it on time.

### Algorithm

1. `Template.render(params)`: build a map from the parameters (split at the first `=`, later keys win, parameters without `=` ignored) and replace each `{key}` with its value or nothing.
2. `send(t, user, template, params)`: drain retries due by `t`. Unknown template: `-1`. Render the text once. For each channel in the fixed order, skip it when the user has no address there or switched it off. Ask the channel's limiter for a slot; a refusal counts as rate limited and skips the channel. Otherwise count the acceptance, format the message with the address, and make an attempt at `t`.
3. Attempt at due time `d`: when the channel is not down at `d`, record the message and count a delivery. When it is down and no retries are left, count a drop. Otherwise schedule the next attempt at `d + 1000 * 2^(k-1)` for the `k`-th retry, keeping the message.
4. Draining retries: while the earliest pending attempt is due at or before now, pop it, count a retry and run step 3 on it. Retries it schedules enter the same heap, so a chain of retries that is all due by now runs completely.
5. `SlidingWindowLimiter.tryAcquire(user, t)`: drop the user's accepted times at or before `t - window`; refuse when `limit` remain, otherwise record `t`.
6. `delivered` and `stats` drain retries, then read the recorded messages or the counters.

### Correctness

Every accepted notification ends in exactly one of three ways: delivered on some attempt, still pending in the heap, or dropped after its third retry. The first attempt happens immediately and each failure schedules exactly one successor with one fewer retry left, until none are left. So `delivered + pending + dropped` equals the number of acceptances on each channel, and nothing is lost silently.

Ordering is deterministic: the heap is ordered by `(due, sequence)`, where `sequence` grows with every scheduled attempt, so equal due times run in scheduling order. Draining before every timestamped call means a retry due at `t` runs before anything new that happens at `t`, which matches the rule in the statement; and since timestamps never decrease, no retry is ever run "in the past" relative to a later call.

The limiter counts accepted notifications in the half-open window `(t - window, t]`, independent of their delivery outcome, so a burst during an outage still respects the limit when the retries land.

### Complexity

- Time: O(b) per send to render; O(log r) per scheduled retry — rendering scans the body once; each channel step is a map lookup and an amortized O(1) limiter check; heap pushes and pops cost O(log r). TypeScript keeps retries in a sorted array, which makes scheduling O(r).
- Space: O(u + d + r) — contacts and limiter windows, delivered messages, and pending retries.

### Trade-offs

- Formatting and addressing at acceptance time freezes the message: a retry delivers exactly what was promised, even if the user changes their address meanwhile. Resolving the address at delivery time would follow address changes but could deliver to an address the user just removed.
- Counting failed notifications against the rate limit protects users from a flood when a channel recovers. Counting only deliveries would let the backlog exceed the limit.
- Lazy retry processing keeps the service single-threaded and testable. A production system would move the heap into a delayed queue or a scheduler, and the attempt logic would stay the same.
- Truncation is a per-channel rule implemented by one class with a limit. If channels grow real behavior (SMS segmenting, push payloads with titles), they become separate classes behind the same interface.

### Pitfalls and edge cases

- Drain retries before handling the call, so that a retry due at the same timestamp runs first.
- Judge an outage at the attempt's due time, not at the time of the call that processes it.
- The outage window is half-open: an attempt at `end` succeeds.
- A switched-off channel is skipped before the rate limit, so it does not use up the user's quota.
- `addContact` on an existing contact replaces the address and switches the channel back on.
- Exactly 20 (SMS) or 30 (push) characters are kept as they are; one more and the text is cut to `limit - 3` characters plus `...`.
- Split parameters at the first `=` only: `b=1=2` gives `b` the value `1=2`.

### Language notes

- Python: `re.sub` with a function renders the template; a dataclass with `order=True` and `field(compare=False)` makes attempts sortable by `(due, sequence)` for `heapq`; `typing.Protocol` describes the channel.
- TypeScript: `String.prototype.replace` with a global regex and a callback renders; there is no heap, so pending retries are a sorted array with binary insertion.
- Java: `Matcher.replaceAll(Function)` renders, with `Matcher.quoteReplacement` so that `$` or `\` in a value is not read as a group reference; records model attempts and contact keys, and a `PriorityQueue` with a two-key comparator orders retries.
- Kotlin: `Regex.replace(input) { ... }` uses the lambda's result literally; a `fun interface Channel` lets email be a lambda; the outage is a `LongRange` built with `until`, so `now in outage` reads like the rule.
- Go: `regexp` is RE2 and in the standard library, so the placeholder pattern is the same as in Python. `ReplaceAllStringFunc` uses the function's result literally, with no `$1` expansion, so a `$` in a value needs no escaping (the trap Java's `quoteReplacement` handles). `strings.Cut` splits a parameter at its first `=`, and the length check counts runes, not bytes.
- Rust: the standard library has no regex engine, so `render` scans for braces by hand: a `{` opens a placeholder only when the next brace after it is a `}`; otherwise it is literal text and the scan resumes right after it, which is what the regex's leftmost-match search does. `Attempt` implements `Ord` on `(due, sequence)` alone, so a `BinaryHeap<Reverse<Attempt>>` pops the earliest retry first and equal due times in scheduling order. Truncation counts `chars()`, not bytes.
