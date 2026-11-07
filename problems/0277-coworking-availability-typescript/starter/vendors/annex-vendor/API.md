# The annex vendor

The company that sells the meeting rooms in the building next door. Your app reaches it at `ANNEX_VENDOR_URL`. This is its contract, and it will not change for you.

## `GET /v2/spaces/open?day=YYYYMMDD`

Note the form of the day: `20270308`, with no dashes. Answers 200 with the spaces that can be booked on that day. A day it has nothing for answers an empty list.

```json
{
  "ok": true,
  "result": {
    "spaces": [
      {"code": "A1", "open": [{"from_minute": 480, "minutes": 45}]},
      {"code": "A2", "open": [{"from_minute": 540, "minutes": 60}]}
    ]
  }
}
```

| Field | Meaning |
|-------|---------|
| `spaces[].code` | The room's name in your answer |
| `spaces[].open[].from_minute` | When the slot starts, in minutes since midnight: 480 is `08:00` |
| `spaces[].open[].minutes` | How long the slot lasts: 45 from 480 ends at `08:45` |

Everything listed can be booked: this vendor leaves out what cannot.

## When it fails

Its status codes say little. Read the body first.

| Answer | Meaning |
|--------|---------|
| 200 with `{"ok": false, "error": {"code": "BUSY", "retry_after_ms": 1000}}` | Too many requests. Wait that many milliseconds and it may answer |
| 200 with `{"ok": false, "error": {"code": "DAY_CLOSED"}}` or another code | It will not answer for this day, and asking again will not change it |
| 5xx | It is down for maintenance, for at least 15 minutes. Do not ask again |

A slow answer is also possible: it does not promise how long one takes.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `maintenance` | Every request answers 503 |
| `busy` | Every request answers 200 with the `BUSY` error, and `retry_after_ms` of 1000 |

Run your app against one: `cstudy dev --scenario annex-vendor=maintenance`. In a test, `setScenario` in `tests/vendorScenario.ts` does the same.
