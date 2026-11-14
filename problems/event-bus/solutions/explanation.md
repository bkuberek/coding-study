# Event Bus: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| topic-matcher | optimal | O(s p k^2) per publish; O(m) per poll or drain | O(s p + e) | default answer; routing, matching and overflow each live in one class |

Here `s` is the number of subscribers, `p` the patterns per subscriber, `k` the number of segments in a topic or pattern, `m` the number of events taken, and `e` the number of events waiting in inboxes and the dead-letter queue.

## Approach: topic-matcher (Subscribers with compiled patterns and bounded inboxes)

### Intuition

Publish-subscribe exists to keep publishers ignorant of subscribers, so the bus is a router and nothing more. The interesting rules sit at its edges: whether a topic matches a pattern (a small string-matching problem with two wildcards), whether a subscriber accepts an event (its inbox policy), and what happens to refused events (the dead-letter queue). Each becomes a class with one question to answer, and `publish` is a short loop that connects them. Pull-based inboxes keep everything synchronous, which is what makes ordering and failure handling exact.

### Algorithm

1. `TopicPattern(text)` splits the pattern into segments once. `matches(topic)` decides whether segments from position `p` match topic words from `w`:
   1. At the end of the pattern: match only at the end of the topic.
   2. `#`: either skip it (`p + 1, w`) or let it swallow one word (`p, w + 1`).
   3. `*` or a literal: needs a word that `*` accepts or that equals the literal, then `p + 1, w + 1`.
2. `subscribe` creates the subscriber on first use and adds a pattern object under its text, refusing an exact duplicate; `unsubscribe` removes it.
3. `publish(topic, payload)`: collect the subscribers with any matching pattern, sort them by id, and offer the event to each. A subscriber accepts unless it has a limit and its inbox holds that many events; a refusal becomes the dead letter `"<id>:<topic>:<payload>"`. With no interested subscriber, add one dead letter for `-`. Return the number of acceptances.
4. `poll`, `pending`, `setInboxLimit` and `deadLetters` read or change one subscriber or the dead-letter queue; `poll` and `deadLetters` remove what they return, oldest first.

### Correctness

Matching: the recursion considers every way `#` can split the topic (zero or more words) and requires literals and `*` to consume exactly one word, so it returns true exactly when the pattern can produce the topic. Memoization (or the equivalent table in Java and Kotlin) does not change the result.

Delivery: a subscriber is collected once per publish, however many patterns match, so it receives the event at most once. Inboxes are FIFO queues appended in publish order, so each subscriber sees events in publish order. Every event is either accepted by each interested subscriber or recorded as a dead letter for it, and an event nobody wants is recorded once for `-`, so nothing is dropped silently. The ascending-id order makes the dead letters of one publish deterministic. A new limit only affects later `offer` calls, so events already queued stay, as specified.

### Complexity

- Time: O(s p k^2) per publish; O(m) per poll or drain — each of a subscriber's patterns is matched in O(k^2) with memoization, plus sorting the interested subscribers; taking `m` events pops `m` items.
- Space: O(s p + e) — the compiled patterns, plus every event waiting in an inbox or the dead-letter queue.

### Trade-offs

- A trie of pattern segments with `*` and `#` branches finds all matching subscriptions in one walk over the topic, instead of testing every pattern of every subscriber. That is how message brokers route at scale; for a few hundred subscriptions the direct test is clearer.
- Callbacks are the more common in-process API. They make delivery order and failure handling harder: a callback that throws, or that publishes during delivery, needs retry and re-entrancy rules. Inboxes avoid both, and a retry policy (re-deliver, then dead-letter after `n` failures) can be layered on later.
- Dead-lettering on overflow keeps publishers fast and loses nothing, but needs someone to drain the dead-letter queue. Alternatives are dropping the oldest event (good for telemetry) or blocking the publisher (back-pressure); each is a different `offer`.

### Pitfalls and edge cases

- `*` matches exactly one segment; `#` matches zero or more, so `orders.#` matches `orders` itself.
- `#` can appear in the middle: `a.#.z` matches `a.z` and `a.b.c.z` but not `a.b`.
- A subscriber with overlapping patterns must not get duplicates.
- An unrouted event is a dead letter once, not once per subscriber.
- Lowering a limit below the current inbox size keeps the queued events; it only refuses new ones.
- An unsubscribed subscriber still exists: it can poll what is left in its inbox.

### Language notes

- Python: a memoized inner function (`functools.cache`) implements the recursion; `deque` holds inboxes and dead letters; the pattern is a frozen dataclass holding its segments.
- TypeScript: the recursion is memoized in a `Map` keyed by `p * (words + 1) + w`. Inboxes are arrays with a head index, so `take` slices instead of calling `shift()` repeatedly.
- Java: `split("\\.")` needs the escaped dot, because `split` takes a regular expression. The matcher fills a boolean table from the end, which avoids recursion. `LinkedHashMap` keeps patterns in subscription order.
- Kotlin: `split(".")` takes a literal string, unlike Java's `split`. The table is `Array(n) { BooleanArray(m) }`, and `List(n) { inbox.removeFirst().render() }` takes `n` events in order.
- Go: `strings.Split` takes a literal separator, so the dot needs no escape, unlike Java's regex-based `split`. The matcher memoizes in a `[][]int8` table (unknown, match, no match) behind a recursive closure. An inbox and the dead-letter queue are slices consumed from the front, and `Publish` collects the interested subscribers from a map and sorts them by id, because map order is random.
- Rust: each subscriber's inbox owns a clone of the event (the frozen Python object is shared), which keeps the ownership simple. `VecDeque::drain(..count)` takes the first events in one call instead of a pop loop, and `publish` sorts a `Vec<&mut Subscriber>` while the dead-letter queue, a separate field, stays borrowable.
