# Notification Service: Rubric

## Responsibilities

- [ ] Each channel alone decides how a message looks on it (`format`); the sending code never checks which channel it is.
- [ ] Templates own rendering; the service passes parameters and receives text.
- [ ] A limiter owns the sliding window per user, and a channel's state owns its outage and counters.
- [ ] One retry scheduler owns pending attempts and their order; delivery and retry share the same attempt logic.

## Extension points

- [ ] A new channel (chat, webhook) is one class and one registration; `send` does not change.
- [ ] A different retry policy (more attempts, jitter, a cap on the delay) changes the scheduling code in one place.
- [ ] A different rate-limiting algorithm (token bucket, fixed window) replaces the limiter behind the same "try to acquire" call.

## Patterns

- [ ] Strategy for channels: one interface, interchangeable formatting, chosen by channel name.
- [ ] Pipeline in `send`: preference, rate limit, format, deliver or schedule a retry, each step a separate concern.
- [ ] Exponential backoff with a bounded number of retries, and a terminal "dropped" outcome that is counted rather than lost.

## Testability

- [ ] Time is a parameter, and outages are configured with explicit windows, so failures and retries are reproducible without a clock, sleeps or a network.
- [ ] Delivered messages and counters are observable through `delivered` and `stats`.
- [ ] Channels, templates and the limiter can each be tested alone.

## Reference design

```text
NotificationService (facade)
 ├── channels: name -> ChannelState(channel: Channel, limiter?, outage?, counters)
 │                       Channel ◁── EmailChannel, TruncatingChannel(limit)  [SMS 20, PUSH 30]
 ├── contacts: (user, channel) -> Contact(address, enabled)
 ├── templates: id -> Template(body).render(params)
 ├── retries: min-heap of Attempt(due, sequence, user, channel, payload, retriesLeft)
 └── delivered: (user, channel) -> messages
```

`send` drains due retries, renders the template once, then walks the channels in a fixed order. For a channel the user has switched on, it asks the channel's limiter for a slot (counting a refusal as rate limited), formats the message with the user's address, and makes an attempt at `timestamp`. `attempt` delivers when the channel is up at the attempt's due time; otherwise it either schedules the next attempt with the doubled delay or, with no retries left, counts the notification as dropped. Retries run through the same `attempt`, so the success path and the counters are identical for first attempts and retries.

Trade-offs: messages are formatted and addressed when accepted, so a retry delivers what the user was promised even if their address changes meanwhile; resolving the address at delivery time is the alternative when contacts are long-lived. The rate limit counts accepted notifications, including ones that later fail, which protects the user from bursts when the channel comes back. Retries are processed lazily at the next timestamped call, which keeps the service single-threaded and deterministic; a production service would use a scheduler or a delayed queue for the same heap.
