# The room vendor

Your app reaches it at `ROOM_VENDOR_URL`.

## `GET /v1/rooms`

Answers 200 with `{"rooms": [{"room": "<name>", "slots": ["<HH:MM>"]}]}`.

## Scenarios

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |

Run your app against it: `cstudy dev --scenario room-vendor=outage`.
