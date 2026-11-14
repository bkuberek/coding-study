# Notification Service

## Statement

Design a service that notifies users through several channels: email, SMS and push. Users register an address per channel and may switch channels off. Messages come from templates with placeholders. Each channel formats messages its own way, may be rate limited per user, and may be down for a while, in which case the service retries with exponential backoff and finally gives up. Adding a channel later must not touch the sending logic.

Implement the facade class `NotificationService`. Nothing is really sent: delivered messages are recorded, and time is passed in as `timestamp` in milliseconds.

## Input

- `NotificationService()`: a service with the channels `"EMAIL"`, `"SMS"` and `"PUSH"`, no users and no templates.
- `addContact(userId, channel, address)`: sets the user's address on a channel and switches the channel on for them.
- `setPreference(userId, channel, enabled)`: switches a channel on or off for a user who has an address there.
- `addTemplate(templateId, body)`: registers a template such as `"Hi {name}"`.
- `setRateLimit(channel, limit, windowMs)`: from now on, the channel accepts at most `limit` notifications per user in any window `t - windowMs < s <= t`.
- `setOutage(channel, start, end)`: the channel fails every delivery attempt at times `start <= t < end`; replaces an earlier outage of that channel.
- `send(timestamp, userId, templateId, params)`: notifies the user with the rendered template on every channel they have switched on.
- `delivered(timestamp, userId, channel)`: the messages delivered to the user on that channel so far.
- `stats(timestamp, channel)`: the channel's counters.

Rules:

- Rendering: each parameter is `"key=value"`, split at the first `=`; parameters without `=` are ignored, and a later parameter with the same key wins. Every `{key}` in the body becomes its value, or nothing when no parameter has that key.
- Channels are tried in the order `EMAIL`, `SMS`, `PUSH`. For each channel the user has switched on, the rate limit is checked first; a notification over the limit is skipped. Otherwise it is accepted (it counts towards the limit from then on), formatted and addressed at once, and delivered at `timestamp`.
- Formatting: every channel produces `"<address>: <text>"`. Email sends the text as is. SMS keeps texts of up to 20 characters, and push up to 30; a longer text is cut so that it ends in `...` and has exactly the limit's length.
- Retries: when a delivery attempt fails because the channel is down, the next attempt happens 1000 ms later, then 2000 ms after that, then 4000 ms after that. If the third retry fails too, the notification is dropped. A retry keeps the message and the address it was accepted with.
- Every call with a `timestamp` first performs all retries due at or before it, in order of their due time (equal times in the order they were scheduled), each judged at its own due time.

## Output

- `addContact` returns `false` for an unknown channel; `setPreference` returns `false` when the user has no address on that channel.
- `addTemplate` returns `false` when the id exists; `setRateLimit` and `setOutage` return `false` for an unknown channel.
- `send` returns the number of channels that accepted the notification, or `-1` for an unknown template.
- `delivered` returns the messages in delivery order, or an empty list.
- `stats` returns `[delivered, retries, dropped, rateLimited]`: messages delivered, retry attempts made, notifications dropped after their last retry, and notifications skipped by the rate limit. It returns an empty list for an unknown channel.

## Examples

### Example 1

<!-- case: ex1 -->

The first notification goes out on both channels, and its text is short enough for SMS. After `ana` switches SMS off, only email is used; `code` has no parameter this time, so it renders as nothing. The template `nope` does not exist.

### Example 2

<!-- case: ex2 -->

SMS is down until 2500. The attempt at 1000 fails, and so does the first retry at 2000; the second retry at 4000 succeeds. The 30-character text is cut to 20 for SMS. Two retries were made and nothing was dropped.

## Constraints

- At most 1000 calls per test; timestamps never decrease and are at most `10^9`.
- Template bodies have at most 100 characters; ids, user ids and addresses at most 20, without spaces.
- `1 <= limit <= 100` and `1 <= windowMs <= 10^9`; `0 <= start <= end <= 10^9`.

## Follow-ups

- How would you add a "digest" channel that batches a user's notifications into one message per hour?
- What changes when delivery is a real network call that may be slow, and sends must not block each other?

## Hints

### Hint 1

Put formatting behind a channel interface with one method, `format(address, text)`. Email, SMS and push are then two small classes (SMS and push differ only in their limit).

### Hint 2

Keep a sliding window of accepted times per user inside a limiter object attached to the channel.

### Hint 3

Model a pending retry as `(dueTime, sequence, user, channel, message, retriesLeft)` in a min-heap, and drain it at the start of every call that has a timestamp.
