# The room vendor

The company that sells the meeting rooms in the main building. Your app reaches it at `ROOM_VENDOR_URL`. This is its contract, and it will not change for you.

## `GET /v1/rooms/availability?date=YYYY-MM-DD`

Answers 200 with every room it has on that day and each room's slots, in no promised order. A day it has nothing for answers `{"rooms": []}`.

```json
{
  "rooms": [
    {
      "id": "oak",
      "name": "Oak",
      "seats": 6,
      "slots": [
        {"start": "09:00", "end": "10:00", "status": "open"},
        {"start": "10:00", "end": "11:00", "status": "booked"}
      ]
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `rooms[].id` | The room's name in your answer |
| `rooms[].slots[].start`, `end` | Local times, `HH:MM` |
| `rooms[].slots[].status` | `open` can be booked, and `booked` cannot |

## When it fails

| Status | Meaning |
|--------|---------|
| 429 | Too many requests. `Retry-After` says how many whole seconds to wait, when it is there |
| 4xx | Something about the request; asking again will not change it |
| 5xx | Its own trouble, which often passes |

A slow answer is also possible: it does not promise how long one takes.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 500 |
| `rate_limited` | Every request answers 429 with `Retry-After: 1` |
| `slow` | Every request answers as usual, after 3 s |

Run your app against one: `cstudy dev --scenario room-vendor=outage`. In a test, `setScenario` in `tests/vendorScenario.ts` does the same.
