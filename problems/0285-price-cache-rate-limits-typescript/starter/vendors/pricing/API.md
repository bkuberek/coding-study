# The pricing engine

The service that works out each product's price from costs, stock and promotions. It is slow: every answer takes about 200 ms, and some take more than a second. Your app reaches it at `PRICING_URL`. This is its contract, and it will not change for you.

## `GET /v1/prices/{sku}`

Answers 200 with the product's price, in cents:

```json
{"sku": "lamp", "amount_cents": 1250, "currency": "EUR"}
```

`Cache-Control` says how long that price stays good, in the directives of RFC 9111 and RFC 5861:

| Directive | Meaning |
|-----------|---------|
| `max-age=<seconds>` | The price is good for that many seconds. `max-age=0` means it is good for no time at all |
| `no-store` | Do not keep the price |
| `stale-while-revalidate=<seconds>` | Once `max-age` has passed, the old price may still be shown for that many more seconds while a new one is fetched |
| `public` | Anyone may keep it. It says nothing about how long |

A price with no `Cache-Control` says nothing about how long it stays good. The directives may come in any order, separated by commas and spaces.

A SKU the engine does not know answers 404 with `{"error": "unknown sku"}`.

## `PUT /v1/prices/{sku}`

Sets a product's price, from a JSON body such as `{"amount_cents": 1400}`, and answers 204 once it is set. The engine may round or adjust a price it is given, so the price to show afterwards is the one `GET` answers.

## When it fails

| Status | Meaning |
|--------|---------|
| 5xx | Its own trouble, for any request |

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |
| `repriced` | The first `GET` of `lamp` answers 1250 cents, and every later one 1400 |
| `clock_repriced` | The first `GET` of `clock` answers 3900 cents, good for 1 s and stale for 30 more; every later one answers 4200, good for 60 s |

Run your app against one: `cstudy dev --scenario pricing=repriced`. In a test, the helper in your project's `tests/` does the same.
