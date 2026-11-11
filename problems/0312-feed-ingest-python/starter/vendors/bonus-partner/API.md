# The bonus partner

The company that grants bonus points on top of what the program earns. Your app reaches it at `BONUS_URL`. This is its contract, and it will not change for you.

## `GET /v1/bonus?member=<id>&month=YYYY-MM`

Answers 200 with the bonus points the partner grants the member for that month, a whole number, 0 or more.

```json
{"bonus_points": 25}
```

A member the partner has no record of answers 404 `{"error": "no_record"}`. That is a real answer: that member has no bonus.

## When it fails

| Status | Meaning |
|--------|---------|
| 429 | Too many requests. `Retry-After` says how many whole seconds to wait, when it is there |
| 4xx | Something about the request or your access; asking again will not change it |
| 5xx | Its own trouble, which often passes |

A slow answer is also possible: it does not promise how long one takes. It can also answer 200 with a body that is not what is described above.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |
| `ana_flaky` | The first request about `ana` answers 503, and the ones after answer as usual |
| `ana_slow` | Every request about `ana` answers as usual, after 2 s |

Run your app against one: `cstudy dev --scenario bonus-partner=outage`. In a test, the helper in your project's `tests/` does the same.
