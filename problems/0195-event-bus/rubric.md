# Event Bus: Rubric

## Responsibilities

- [ ] A pattern object alone knows the wildcard syntax and answers `matches(topic)`.
- [ ] Each subscriber owns its patterns, its inbox and its limit, and decides whether it accepts an event.
- [ ] The dead-letter queue owns the format and order of undeliverable events.
- [ ] `EventBus` only routes: it finds interested subscribers, offers the event, and sends refusals to the dead-letter queue.

## Extension points

- [ ] A new overflow policy (drop the oldest event, block, spill to disk) changes the subscriber's `offer` only.
- [ ] A different pattern syntax (regular expressions, prefix rules) changes the pattern class only.
- [ ] Callback delivery could replace inboxes behind the same subscriber interface, without changing `publish`.

## Patterns

- [ ] Publish-subscribe (Observer) decouples publishers from subscribers: neither holds a reference to the other.
- [ ] The dead-letter queue is a deliberate failure channel, so a full inbox or an unrouted event is visible instead of silently lost.
- [ ] Patterns are value objects, compiled once at subscription time.

## Testability

- [ ] Delivery is synchronous and pull-based (`poll`), so tests observe exactly which events arrived, in order, without threads or sleeps.
- [ ] Pattern matching can be tested alone with pairs of patterns and topics.
- [ ] The serving order inside one `publish` is defined (ascending subscriber id), so dead letters are deterministic.

## Reference design

```text
EventBus (facade: routing)
 ├── subscribers: id -> Subscriber(patterns: TopicPattern[], inbox: Event queue, limit)
 └── DeadLetterQueue: "<subscriber>:<topic>:<payload>" queue
TopicPattern.matches(topic)   Subscriber.wants(topic), offer(event), take(n)
```

`subscribe` creates the subscriber on first use and stores a `TopicPattern` per distinct pattern string, in subscription order. `publish` builds an `Event`, collects the subscribers that want it (any pattern matches, so a subscriber counts once), sorts them by id, and offers the event to each. `offer` appends to the inbox unless a limit is set and reached; a refusal becomes a dead letter for that subscriber. When nobody wants the event, it becomes one dead letter with subscriber `-`.

`TopicPattern.matches` is a memoized recursion over pattern and topic positions: a literal or `*` consumes one segment on both sides; `#` either moves on in the pattern or consumes one topic segment. With at most six segments, it is O(k^2) per check.

Trade-offs: checking every subscriber's patterns on each publish is O(subscribers x patterns). A trie of pattern segments (with `*` and `#` branches) would find all matching subscriptions in one walk, which is how brokers scale to many subscribers. Pull-based inboxes keep the bus deterministic and free of re-entrancy problems (a callback that publishes during delivery), at the cost of making consumers poll.
