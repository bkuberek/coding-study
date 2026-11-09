# Payment Webhook Receiver (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per event | default answer: verify the bytes before anything else, keep applied events by id, and move each order one sequence number at a time |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Only what the provider signed, and only while it is fresh | `src/webhooks/signature.ts`: `isSigned` over the raw bytes with `timingSafeEqual`, and `isTimely`; `parseEvent` in `src/events.ts`, called after both |
| 2 | Each event once | `OrderBook` keeps applied events by id; `isDeepStrictEqual` tells a retry from a reused id |
| 3 | Events in sequence, along the allowed transitions | `NEXT_STATES` and `nextSequence`; an early event waits in a hold per order, and a drain after each event applied |
| 4 | Fill gaps from the provider, and answer so it retries only what can succeed | `src/provider.ts`, one request within 1 s; a failure becomes 503 before anything changes. Unknown types take their place as no-ops. The hold goes |

## Approach: reference (Verify the bytes, then apply each order's events in sequence)

### Intuition

A webhook is a request from the internet that claims to come from the provider. The signature is the only thing that makes the claim true, and it is a claim about bytes: the provider computed an HMAC over the timestamp and the body exactly as it sent them. So the check has to run on those bytes, before anything else touches them. A parsed and re-encoded body is a different string, and it fails every honest delivery.

The timestamp is inside the signed text for a reason. Without it, a delivery captured once would be valid forever. With it, a captured delivery is valid for 300 s, and inside that window it is just a duplicate, which the idempotency rule already makes harmless. The window and the id store are one defence: each covers the time the other cannot.

Delivery order is not event order. The provider numbers each order's events, so the receiver can rebuild the order they happened in, and apply them through a small state machine that would refuse a refund of a payment that never succeeded. An event that arrives early is either held until the gap closes, or the gap is filled from the provider's own record. Either way, nothing is applied out of turn.

Then there is the answer itself. The provider reads the status code as an instruction: 2xx means delivered, 4xx means never send this again, 5xx means try later. A bad signature is a 4xx, because no retry will fix it. A gap the provider's API cannot fill right now is a 5xx, because a later attempt may find it filled. And a 5xx must leave no trace, or the retry it asks for is taken for a duplicate.

### Say it out loud

"First I verify. I read the raw body, compute the HMAC of the timestamp, a dot and those bytes with the shop's secret, check the header is 64 hex digits, and compare in constant time. Only then do I check the timestamp is within five minutes, and only then do I parse JSON. Each failure is a 4xx, because the provider retrying will never make it valid.

"Then idempotency. I keep every event I have applied, by id. A retry has the same id and the same content, so I acknowledge it and change nothing. The same id with different content is not a retry, so I refuse it.

"Then ordering. Each order has a sequence counter. The next event is applied if the state machine allows it. An event ahead of the counter means something is missing, so I ask the provider for the events in between, once, with a one-second timeout. If that works I apply them in order. If it doesn't, I answer 503 and change nothing, so the provider's retry finds everything as it was."

### Algorithm

1. Read the body as bytes. Without both headers, or with a signature that is not 64 hex digits, answer 401 `invalid signature`.
2. Compute the HMAC-SHA256 of the timestamp, `.` and the bytes, and compare with `timingSafeEqual`. A mismatch is 401 `invalid signature`.
3. If the timestamp is not digits, or more than 300 s from `nowSeconds()`, answer 401 `timestamp outside tolerance`.
4. Parse the bytes as JSON and check the event's fields. Anything else is 400 `invalid event`.
5. If the id has been applied before, answer 200 `duplicate` when the event is deeply equal to the one applied, else 409 `event id reused`.
6. Compare the event's `sequence` with the order's next. Below it, 409. Above it, fetch the order's events from the provider and take the missing ones; any failure is 503, before anything changes. Apply the missing ones in order.
7. Apply the event: an unknown type is `ignored`, a transition the machine allows is `applied`, and any other is 409 `illegal transition`.

### Design

- `src/server.ts`: the routes, as a lookup that answers 404 and 405 in one place, `readBody`, which returns a `Buffer`, and the wiring of the receiver.
- `src/webhooks/signature.ts`: `isSigned`, a type guard that checks the format and then compares digests in constant time, and `isTimely`. Both are pure and read only what arrived.
- `src/webhooks/receiver.ts`: `WebhookReceiver.receive`, the checks in their order, each with its status. `#fillGap` asks the provider and applies what it lists.
- `src/events.ts`: `parseEvent` and `eventFrom`, which keep the whole object, so two events compare whole.
- `src/orders.ts`: `OrderBook`, with the state per order, the applied events by id, `nextSequence` and `place`, and `NEXT_STATES`, the state machine as data.
- `src/provider.ts`: `ProviderClient.eventsBetween`, one request under `AbortSignal.timeout(1000)`, which throws `ProviderUnavailable` for a failed request, a broken body, the wrong shape, or a list with a hole.
- `src/clock.ts`: unchanged from the starter.

Not graded, and worth discussing:

- **Persistence.** Everything is in memory, so a restart forgets every id and every order. A real receiver stores the applied ids and the order states in one transaction, so a crash between them cannot apply an event without remembering it.
- **Acknowledge first, process later.** A common design writes the verified raw delivery to a queue, answers 2xx at once, and processes from the queue. The provider never waits, and your own retries take over from its. It moves the work, not the rules: the queue's consumer still needs everything above.
- **Forgetting ids.** With a 300 s window, an id older than the window plus the provider's retry period can never come back validly. Here the retry period is three days, so that is how long an id must be kept.
- **Concurrent deliveries.** The grader sends one request at a time. Two deliveries for one order at once could both find the same gap and both apply the fetched events. A per-order lock, or a promise chain per order, makes them take turns.
- **Secret rotation.** Accept a signature made with either the old or the new secret during the overlap, and drop the old one when the provider confirms it no longer signs with it.

### Correctness

Nothing reaches `JSON.parse` before `isSigned` and `isTimely` hold, so an unsigned or stale body cannot even make the app parse it, and every refusal of the first three checks is a 4xx. `isSigned` checks the header's form before `timingSafeEqual`, so the compare always meets two 32-byte buffers and cannot throw. An event's id is stored only inside `OrderBook.place`, after the transition is allowed, so a refused or failed delivery leaves no id behind, and the provider's retry is processed as new. `place` is only called with the order's next sequence number, so each order's state passes through its events in their own order, and `NEXT_STATES` holds at every step. A gap is fetched and checked in full before the first missing event is applied, so a 503 changes nothing.

### Complexity

- Time: per request — a hash of the body and constant-time work per event applied, plus at most one request to the provider, which costs one pass over the order's events
- Space: per event — every applied event is kept by id, with its content, and one small record per order

### Trade-offs

The reference keeps whole events, not just their ids, to tell a retry from a reused id. A hash of each event's canonical form would use less memory. A hash of the raw body would not work, because a retry may be written with other spacing.

Filling a gap synchronously keeps the answer honest: 200 means applied. It costs up to a second of waiting on the provider, inside a 2 s budget. Holding the event and fetching in the background would answer faster, at the price of a background job and its own failure handling.

Answering 503 when the gap cannot be filled hands the retry to the provider, which already stores the event durably and retries for days. Holding it in memory would lose it on a restart, after the provider had been told it was delivered.

`node:http` and `node:crypto` keep the install small and the raw body in plain sight. A framework with a JSON body parser would need its raw-body option, or the signature would be checked against the wrong bytes.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Parses first, then verifies `JSON.stringify` of the event | A re-encoded body is not the bytes the provider signed: every honest delivery fails | `v1`: `status: expected 200, got 401`, and `h13` |
| Parses before verifying | A forged body is parsed, and a broken forged one answers 400 rather than 401 | `h10` |
| Signs or checks the body alone, without the timestamp | A captured delivery stays valid forever with a fresh timestamp | `h5` |
| Compares signatures with `===` | Leaks, through timing, how much of a forged signature was right. No case can measure it, so it is left to review | None: the reason to use `timingSafeEqual` |
| `timingSafeEqual` with no length check | Throws on a short signature, so a forged request becomes a 500, and the provider retries it | `h4` |
| No timestamp window | A delivery captured once is valid forever | `h6`, `h8`, `h17` |
| `>= 300` for the window, or `Number(timestamp)` unchecked | Refuses a delivery exactly 300 s old, or lets `NaN` through every comparison | `h7`, `h9` |
| Answers 500 for a bad signature | The provider retries a request that will never be valid | `v3`, `h1` to `h5` |
| Treats every repeated id as an error | The provider's retries are refused, and it stops sending them | `v4`, `h18`, `h20` |
| Treats every repeated id as a duplicate | Another event under a used id is acknowledged and lost | `v5`, `h19` |
| Compares the raw bodies of a retry | A retry written with other spacing looks like a reused id | `h18` |
| Applies events in arrival order | A refund that arrives first is undone by the payment that arrives after it | `v6`: `body.state: expected "refunded", got "succeeded"`, and `h22`, `h23` |
| No state machine | A refund of a failed payment, or a payment after its refund, is applied | `v7`, `h24` |
| Retries the events API inside the request, or waits for its `Retry-After` | Delays the answer the provider is waiting for, when its next attempt is the retry | `h32`: `expected 1 request, saw 2` |
| No timeout on the events API | The provider gives up waiting and redelivers while your app still waits | `h31`: `status: expected 503, got 200`, after 3 s |
| Marks the event processed before the gap is filled | The 503 asks for a retry, and the retry is taken for a duplicate | `h38`: `outcome: expected "applied", got "duplicate"` |
| Fetches on every event | Costs a request when nothing is missing | `h30`, `h42`: `expected 0 requests` |
| Answers 4xx for an event type it does not know | The provider stops sending something it was right to send | `h40` |

**Edge cases.**

- A body that is not JSON but carries a valid signature is 400, and one with an invalid signature is 401. Which one depends only on the order of the checks (`h10`, `h11`).
- A timestamp in the future is as suspect as an old one (`h8`).
- The same delivery sent twice inside the window, byte for byte, is a duplicate, not an attack to refuse: it changes nothing either way (`h20`).
- A late retry of an event an order has moved past must change nothing, even though applying it again would be a legal transition from an earlier state (`h16`).
- An event that waited for the one before it is applied when the gap closes, and its id is then taken like any other (`h28`, `h39`).
- `failed` to `failed` is allowed: a customer can fail twice before paying (`h26`).
- An ignored event still takes its place, so the event after it finds no gap (`h41`, `h42`).
- A list from the provider can lag behind its webhooks, so check it holds every missing event before you apply any (`h35`).
