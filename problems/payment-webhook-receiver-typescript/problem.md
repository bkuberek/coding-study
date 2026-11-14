# Payment Webhook Receiver (TypeScript)

## Statement

An online shop takes card payments through a payment provider. The provider tells the shop what happened to each order's payment, that it succeeded, failed, was refunded or was disputed, by sending webhooks: signed HTTP requests to the shop's API. Anyone on the internet can send a request to that address, the provider sends some events twice, and it promises nothing about their order.

Build the receiver, in levels: it trusts only what the provider signed, applies each event once, and keeps every order's state right whatever order the news arrives in. `cstudy` runs your app in a Docker sandbox with a mock server for the provider's events API. The graded webhooks come from the grader, and it judges your app by what it answers and by what the provider's API saw it ask. The shop, the provider, its headers, the secret and every number are invented.

**The clock is frozen.** The graded webhooks were signed once, when this problem was written, so your app's "now" is `CLOCK_NOW` from its environment: `1803902400`, which is 2027-03-01 12:00:00 UTC. `nowSeconds()` in `src/clock.ts` reads it. Use it wherever your app needs the time. A real service would read its real clock, and nothing else would change.

## Input

HTTP requests. `POST /webhooks/payments` receives the provider's deliveries, as `vendors/payment-provider/API.md` describes them, and `GET /orders/{order}` asks what your app knows about an order.

A delivery carries an event as its JSON body, with two headers:

- `Provider-Timestamp`: when the provider signed it, in whole seconds since the Unix epoch.
- `Provider-Signature`: the HMAC-SHA256 of the timestamp, a `.`, and the body's bytes exactly as they came, keyed with `WEBHOOK_SECRET`, as 64 lowercase hex digits.

```json
{"id": "evt_9c0d9cf58c6a", "type": "payment.succeeded", "order": "ord_1001", "sequence": 1, "amount": 2275, "currency": "EUR", "created": 1803901830}
```

An event is a JSON object with a non-empty string `id`, `type` and `order`, and a whole number `sequence` from 1. Other fields may be there, and your app keeps them as they came.

## Output

JSON, always with `Content-Type: application/json`. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

`GET /orders/{order}` answers 200 with the order's state and the `sequence` of the last event applied to it, or 404 with `{"error": "unknown order"}` when no event has been applied to it:

```json
{"order": "ord_1002", "state": "succeeded", "sequence": 1}
```

## Project

`cstudy start` copies the service into `projects/payment-webhook-receiver-typescript/`, and `cstudy dev` runs it with the provider's events API. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. Its `readBody` gives you the body's bytes as they arrived.
- `src/orders.ts`: `OrderBook`, each order's state, kept in memory. There is no database.
- `src/events.ts`: `PaymentEvent`, the shape of an event.
- `src/clock.ts`: `nowSeconds()`, the frozen clock.
- `tests/`: your tests, run by `cstudy test`, with `tests/provider.ts` to sign and send a delivery as the provider would, and to set a visible scenario on its events API.
- `vendors/payment-provider/API.md`: the provider's contract, for reading. Nothing depends on this copy.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. The app has no network beyond its stack. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. The app keeps its state in memory for the whole run, so each case uses orders and events of its own.

## Level 1: Verify the signature

The starter applies whatever arrives at `POST /webhooks/payments`. Make it apply only what the provider signed, and only while the signature is fresh. Check in this order, and answer the first rule that fails:

| The delivery | Status | Body |
|--------------|--------|------|
| Has no `Provider-Signature` or no `Provider-Timestamp`, or its signature is not the provider's for that timestamp and body | 401 | `{"error": "invalid signature"}` |
| Is signed, but its timestamp is not whole seconds within 300 s of now, either way | 401 | `{"error": "timestamp outside tolerance"}` |
| Is signed and fresh, but its body is not an event | 400 | `{"error": "invalid event"}` |
| Is signed and fresh, and holds an event | 200 | `{"outcome": "applied"}` |

Applying an event sets its order's state from its type: `payment.succeeded` to `succeeded`, `payment.failed` to `failed`, `payment.refunded` to `refunded` and `payment.disputed` to `disputed`. The order's `sequence` becomes the event's. Level 4 says what to do with any other type.

- The signature covers the bytes that came, not the event they describe. Compute it before you parse anything, and over the body exactly as it arrived.
- Compare it in constant time, with `timingSafeEqual` from `node:crypto`, so the time an answer takes says nothing about how much of a forged signature was right.
- A 4xx tells the provider to stop sending: right for a request that will never be valid. A 5xx asks it to try again.

### Example 1

<!-- case: v1 -->

The provider signs `{"id": "evt_9c0d9cf58c6a", "type": "payment.succeeded", "order": "ord_1001", "sequence": 1, "amount": 2275, "currency": "EUR", "created": 1803901830}` at `1803902370`, 30 s before now: the delivery answers 200 with `{"outcome": "applied"}`.

### Example 2

<!-- case: v2 -->

After a signed `payment.succeeded` for `ord_1002`, `GET /orders/ord_1002` answers 200 with `{"order": "ord_1002", "state": "succeeded", "sequence": 1}`.

### Example 3

<!-- case: v3 -->

The same kind of event for `ord_1003`, signed with a secret that is not the shop's: 401 with `{"error": "invalid signature"}`, and the order stays unknown.

## Level 2: Duplicates and replays

Each event has an `id`, and the provider delivers every event at least once. Its retry carries the same event under the same id, signed again with a new timestamp, and not always written with the same spacing or key order. After the checks of level 1:

| The event | Status | Body |
|-----------|--------|------|
| Has an id your app has already applied, and is the same event: the same JSON value, field for field | 200 | `{"outcome": "duplicate"}`, and nothing changes |
| Has an id your app has already applied, with any field different | 409 | `{"error": "event id reused"}`, and nothing changes |

The timestamp check of level 1 is your defence against replays. Someone who captured a delivery can send it again, byte for byte, but not sign a new timestamp. Inside the 300 s window a replay is a duplicate and changes nothing. Outside it, the delivery is refused before any id is looked up.

### Example 1

<!-- case: v4 -->

`ord_2001`'s `payment.succeeded` arrives at `1803902310`, then again, signed at `1803902380`: the second delivery answers 200 with `{"outcome": "duplicate"}`.

### Example 2

<!-- case: v5 -->

After `ord_2002`'s `payment.succeeded`, a delivery with the same `id` holds a `payment.refunded` of sequence 2: 409 with `{"error": "event id reused"}`.

## Level 3: Events out of order

A payment moves along these transitions and no others. An order with no event applied yet is `pending`.

| From | To |
|------|----|
| `pending` | `succeeded`, `failed` |
| `failed` | `failed`, `succeeded`: a customer can try again |
| `succeeded` | `refunded`, `disputed` |
| `refunded`, `disputed` | Nothing |

The provider numbers each order's events by `sequence`, and that is their order, whatever order they arrive in. A refund can arrive before the payment it refunds. Apply each order's events in `sequence` order:

| The event | Status | Body |
|-----------|--------|------|
| Is the order's next, and its transition is allowed | 200 | `{"outcome": "applied"}`; then apply any events held for the order that now come next |
| Is the order's next, and its transition is not allowed | 409 | `{"error": "illegal transition"}`, and nothing changes |
| Is ahead of the order's next, so an event before it is missing | 202 | `{"outcome": "held"}`: keep it, and apply it once the events before it are in |
| Has a `sequence` the order has already passed, under a new id | 409 | `{"error": "illegal transition"}`, and nothing changes |

An event's id counts as applied, for level 2, only once the event is applied in its place. A held event is not applied yet.

### Example 1

<!-- case: v6 -->

`ord_3001`'s `payment.refunded`, sequence 2, arrives before its `payment.succeeded`, sequence 1. Then `GET /orders/ord_3001` answers 200 with `{"order": "ord_3001", "state": "refunded", "sequence": 2}`.

### Example 2

<!-- case: v7 -->

`ord_3002`'s payment failed, then a `payment.refunded` of sequence 2 arrives: 409 with `{"error": "illegal transition"}`. A payment that failed has nothing to refund.

## Level 4: Answer the provider and reconcile

A held event waits for a delivery that may never come: the provider may have given up on it, or sent it while your app was down. So stop waiting. When an event is ahead of its order's next, ask the provider for the events in between, with one request to `GET /v1/orders/{order}/events` at `PAYMENT_PROVIDER_URL`, then apply them in order, then the event itself. They are events like any other, applied and taken by id. This replaces holding.

The provider waits 2 s for your answer. When the gap cannot be filled, answer so that it delivers the event again later, when your app may be able to:

| The events API | Your app |
|----------------|----------|
| Answers with every missing event | Applies them, then the event: 200 `{"outcome": "applied"}` |
| Answers 5xx or 429, or 404 for an order it does not know yet | 503 `{"error": "provider unavailable"}`, at once |
| Takes more than 1 s to answer | Gives up on it: 503, so the provider is not left waiting |
| Answers 200 with a body that is not what the API documents, or a list that lacks a missing event | 503 |

- One request to the events API per delivery, whatever it answers. The provider's next attempt is your retry, and it does not wait for you.
- A delivery answered 503 leaves no trace: nothing applied, no id taken. Otherwise its next attempt looks like a duplicate, and the event is lost.
- An event with no gap before it asks the events API nothing.

The provider also adds event types over time. An event of a type this service does not handle is acknowledged with 200 and `{"outcome": "ignored"}`: it leaves the order's state as it is, and still takes its place in the sequence and its id.

### Example 1

<!-- case: v8 -->

`ord_4001`'s `payment.refunded`, sequence 2, arrives first. Your app asks the events API once, applies the `payment.succeeded` it lists as sequence 1, then the refund: 200 with `{"outcome": "applied"}`.

### Example 2

<!-- case: v9 -->

The same for `ord_4002`, with the events API answering 503 to everything: 503 with `{"error": "provider unavailable"}`, after one request to it.

## Constraints

- A delivery is judged on its bytes as they came: verify before you parse, and compare signatures in constant time.
- A 4xx only for a delivery that will never be accepted, a 5xx only when a later attempt could be, and nothing slower than the provider's 2 s.
- At most one request to the events API for one delivery, and none when there is no gap.
- Your app reads the time only through `nowSeconds()`, reaches the provider only through `PAYMENT_PROVIDER_URL`, and listens on all interfaces inside the container.

## Follow-ups

- The shop rotates its webhook secret. For a while some deliveries are signed with the old one and some with the new. What changes in your check, and when can the old secret go?
- Your app keeps every id it has applied, forever. With the 300 s window, which ids could it forget, and when? What goes wrong if it forgets an id too soon?
- Your app restarts and loses its memory. Which deliveries would it now get wrong, and what would a database have to hold for it not to?
- Two deliveries for the same order arrive at the same moment, and both find a gap. What could go wrong, and how would you make one wait for the other?
- An event is refused as an illegal transition. Nobody will deliver it again. Who should hear about it, and how?

## Hints

### Hint 1

Read the body into a buffer once, and pass those same bytes to the signature and, only after it holds, to `JSON.parse`. Anything parsed and written out again is a different string.

### Hint 2

`timingSafeEqual` throws when its two buffers differ in length. Check that the header is 64 hex digits before you compare, so a short signature is a 401 and not a crash.

### Hint 3

`Number("abc")` is `NaN`, and every comparison with `NaN` is false, so `Math.abs(now - Number(timestamp)) > 300` lets it through. Check the form of the timestamp first.

### Hint 4

Keep the events you have applied by id, with their content, so one lookup tells a retry from a reused id. Keep per order the sequence it has reached: an event is late, next or early by comparing with it.

### Hint 5

Fill a gap completely or not at all. Fetch, check that every missing event is there, then apply. If anything fails, return before you have changed or remembered anything.
