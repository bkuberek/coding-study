# Event Bus

## Statement

Design an in-process event bus. Publishers send events to topics such as `orders.eu.created`; subscribers register topic patterns, possibly with wildcards, and each receives the matching events in its own inbox, in publish order. A subscriber may cap its inbox; events it cannot take, and events nobody wants, go to a dead-letter queue so that nothing is lost silently.

Implement the facade class `EventBus`. Delivery is synchronous: subscribers read their inbox with `poll`, so nothing runs in the background.

## Input

- `EventBus()`: a bus with no subscribers.
- `subscribe(subscriberId, pattern)`: the subscriber receives the events whose topic matches `pattern`. A subscriber exists from its first `subscribe` on, even after it unsubscribes from everything.
- `unsubscribe(subscriberId, pattern)`: removes one of the subscriber's patterns.
- `publish(topic, payload)`: sends an event.
- `poll(subscriberId, maxEvents)`: takes up to `maxEvents` events from the subscriber's inbox.
- `pending(subscriberId)`: how many events wait in the inbox.
- `setInboxLimit(subscriberId, limit)`: from now on, the inbox accepts an event only while it holds fewer than `limit` events. Events already in it stay. Without a limit, the inbox is unbounded.
- `deadLetters(maxEvents)`: takes up to `maxEvents` entries from the dead-letter queue.

Matching and delivery rules:

- Topics and patterns are segments separated by dots. In a pattern, `*` matches exactly one segment, `#` matches zero or more segments (anywhere in the pattern), and any other segment matches only itself, case-sensitively.
- A subscriber receives an event at most once, however many of its patterns match.
- Within one `publish`, the interested subscribers are served in ascending order of id. A subscriber whose inbox is full gets nothing, and the event goes to the dead-letter queue for that subscriber. An event that matches no subscriber goes to the dead-letter queue once, with the subscriber `-`.

## Output

- `subscribe` returns `false` when the subscriber already has exactly this pattern; `unsubscribe` returns `false` when it does not have it.
- `publish` returns the number of subscribers whose inbox accepted the event.
- `poll` returns the events oldest first as `"<topic>:<payload>"`, removing them; an unknown subscriber gets an empty list.
- `pending` returns the inbox size, or `-1` for an unknown subscriber.
- `setInboxLimit` returns `false` for an unknown subscriber.
- `deadLetters` returns entries oldest first as `"<subscriberId>:<topic>:<payload>"`, removing them.

## Examples

### Example 1

<!-- case: ex1 -->

`orders.*` matches `orders.created` only, since `*` needs exactly one segment. `orders.#` matches all three topics, including `orders` itself, because `#` may match nothing. Nobody publishes to `payments.created`, so `ledger` has nothing waiting.

### Example 2

<!-- case: ex2 -->

`slow` accepts one event, so `y` and `z` become dead letters for `slow`. After it unsubscribes, `w` matches nobody and is dead-lettered with `-`. The first event is still in the inbox.

## Constraints

- At most 1000 calls per test.
- Topics have 1 to 6 segments of 1 to 10 letters or digits; patterns have 1 to 6 segments, each such a word, `*` or `#`.
- Payloads are 1 to 10 letters or digits; subscriber ids are 1 to 10 lowercase letters or digits.
- `0 <= maxEvents, limit <= 1000`.

## Follow-ups

- How would you deliver to callbacks instead of inboxes, and retry a callback that throws?
- How would matching stay fast with ten thousand subscribers?

## Hints

### Hint 1

Turn each pattern into an object that answers `matches(topic)`. The subscriber asks each of its patterns and stops at the first match, which also gives "at most once" for free.

### Hint 2

Matching with `#` is a small recursion over (pattern position, topic position): `#` either matches nothing and moves on in the pattern, or swallows one topic segment and stays.

### Hint 3

Give the subscriber an `offer(event)` that returns `false` when the inbox is full; the bus then sends the event to the dead-letter queue.
