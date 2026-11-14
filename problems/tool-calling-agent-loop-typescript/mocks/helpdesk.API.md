# The helpdesk

Where the support team tracks its work. Your app opens tickets in it through the `create_ticket` tool, at `HELPDESK_URL`. This is its contract, and it will not change for you.

## `POST /v1/tickets`

Takes `{"subject": "Damaged parcel, order A-1187", "body": "The customer reports ...", "priority": "high"}`, where `priority` is `low`, `normal` or `high`, and answers 201:

```json
{"id": "T-3001", "status": "open", "subject": "Damaged parcel, order A-1187", "priority": "high"}
```

Every request opens a new ticket, the same one twice included.

## When it fails

| Status | Meaning |
|--------|---------|
| 5xx | Its own trouble, which often passes |

## Scenarios

These change how the helpdesk answers. They are what you can try for yourself, and not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |

Run your app against one: `cstudy dev --scenario helpdesk=outage`. In a test, `setScenario` in your project's `tests/mockControl.ts` does the same.
