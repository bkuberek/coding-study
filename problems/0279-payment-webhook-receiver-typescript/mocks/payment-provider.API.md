# The payment provider

The company that takes the shop's card payments. It tells your app what happened to each order's payment by webhook, and answers questions about an order through its events API, which your app reaches at `PAYMENT_PROVIDER_URL`. This is its contract, and it will not change for you.

## Webhooks

It sends each event as a `POST` to the shop's webhook, `/webhooks/payments` on your app, with the event as a JSON body and two headers:

| Header | Value |
|--------|-------|
| `Provider-Timestamp` | When this delivery was signed, as whole seconds since the Unix epoch |
| `Provider-Signature` | The HMAC-SHA256 of the timestamp, a `.`, and the body's bytes exactly as sent, keyed with the shop's webhook secret (`WEBHOOK_SECRET`), as 64 lowercase hex digits |

For timestamp `1803902370` and body `{"id": "evt_9c0d9cf58c6a", ...}`, the signed text is `1803902370.{"id": "evt_9c0d9cf58c6a", ...}`, byte for byte.

### Events

```json
{"id": "evt_9c0d9cf58c6a", "type": "payment.succeeded", "order": "ord_1001", "sequence": 1, "amount": 2275, "currency": "EUR", "created": 1803901830}
```

| Field | Meaning |
|-------|---------|
| `id` | The event's own id. Every delivery of this event carries it |
| `type` | What happened: `payment.succeeded`, `payment.failed`, `payment.refunded` or `payment.disputed`. Other types are added over time, without notice |
| `order` | The shop's order the payment belongs to |
| `sequence` | The event's place among the order's events: 1, 2, 3, with no gaps and no repeats |
| `amount`, `currency` | The payment's amount in minor units, such as cents, and its currency |
| `created` | When the event happened, as whole seconds since the Unix epoch |

### Deliveries

- Every event is delivered at least once, and the order of deliveries is not promised: an order's event 2 can arrive before its event 1.
- It waits 2 s for an answer, and reads the status:

| Your answer | What it does |
|-------------|--------------|
| 2xx | Counts the event as delivered, and does not send it again |
| 4xx | Counts it as refused, and does not send it again either |
| 5xx, or nothing within 2 s | Sends it again later, for up to three days |

- Each attempt is signed anew, with its own timestamp. A retry carries the same event, though not always written with the same spacing or key order.

## `GET /v1/orders/{order}/events`

Answers 200 with every event it has for the order so far, by `sequence`, each exactly as its webhook carries it:

```json
{
  "order": "ord_4001",
  "events": [
    {"id": "evt_ee5649d28675", "type": "payment.succeeded", "order": "ord_4001", "sequence": 1, "amount": 2100, "currency": "EUR", "created": 1803901830}
  ]
}
```

It records an event a moment before it sends the webhook, and can lag behind for a moment, so a list may not yet hold every event. An order it does not know answers 404.

## When the API fails

| Status | Meaning |
|--------|---------|
| 429 | Too many requests. `Retry-After` says how many whole seconds to wait |
| 4xx | Something about the request; asking again will not change it |
| 5xx | Its own trouble, which often passes |

A slow answer is also possible: it does not promise how long one takes.

## Scenarios

These change how the events API answers. They are what you can try for yourself, and not all it can do. Webhooks are not affected: in the sandbox, you or the grader send those.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |
| `slow` | Every request answers as usual, after 3 s |
| `rate_limited` | Every request answers 429 with `Retry-After: 1` |

Run your app against one: `cstudy dev --scenario payment-provider=outage`. In a test, the helper in your project's `tests/` does the same.
