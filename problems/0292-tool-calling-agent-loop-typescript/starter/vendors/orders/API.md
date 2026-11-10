# The order system

The shop's orders and their refunds. Your app reaches it through the `lookup_order` and `issue_refund` tools, at `ORDERS_URL`. This is its contract, and it will not change for you.

## `GET /v1/orders/{order_id}`

Answers 200 with the order:

```json
{"id": "A-1042", "status": "shipped", "placed_on": "2027-02-27", "shipped_on": "2027-03-02", "delivered_on": null,
 "tracking": "PX-55102", "total_cents": 4599, "currency": "EUR", "customer_note": null}
```

| Field | Meaning |
|-------|---------|
| `status` | `placed`, `packed`, `shipped` or `delivered` |
| `placed_on`, `shipped_on`, `delivered_on` | Dates, or null until they happen |
| `tracking` | The parcel's tracking number, or null before it ships |
| `total_cents`, `currency` | What the customer paid, in minor units such as cents |
| `customer_note` | What the customer typed into the note field at checkout, or null |

An order it does not have answers 404 with `{"error": "order not found"}`.

## `POST /v1/refunds`

Takes `{"order_id": "A-2052", "amount_cents": 3250, "reason": "Cancelled before shipping"}` and answers 201:

```json
{"id": "R-7001", "order_id": "A-2052", "amount_cents": 3250, "status": "issued"}
```

The money leaves at once, and nothing here takes it back.

## When it fails

| Status | Meaning |
|--------|---------|
| 404 | No such order |
| 5xx | Its own trouble, which often passes |

## Scenarios

These change how the order system answers. They are what you can try for yourself, and not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |

Run your app against one: `cstudy dev --scenario orders=outage`. In a test, `setScenario` in your project's `tests/mockControl.ts` does the same.
