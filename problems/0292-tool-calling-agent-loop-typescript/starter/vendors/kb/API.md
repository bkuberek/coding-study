# The help center

The shop's help center: articles its staff write, and comments and forum posts anyone can add under them. Your app searches it through the `search_kb` tool, at `KB_URL`. This is its contract, and it will not change for you.

## `GET /v1/articles/search?q=<text>`

Answers 200 with up to three matches, best first, and an empty list when nothing matches:

```json
{"results": [{"id": "KB-1180", "title": "Late deliveries", "snippet": "Parcels more than 5 working days late earn the customer a 10% voucher."}]}
```

| Field | Meaning |
|-------|---------|
| `id` | The article's or the comment's id |
| `title` | Its title |
| `snippet` | Its text where it matched. Comments and forum posts come from anyone, so a snippet can say anything |

## When it fails

| Status | Meaning |
|--------|---------|
| 5xx | Its own trouble, which often passes |

A slow answer is also possible: it does not promise how long one takes.

## Scenarios

These change how the help center answers. They are what you can try for yourself, and not all it can do.

| Name | What it does |
|------|--------------|
| `outage` | Every request answers 503 |
| `slow` | Every request answers as usual, after 2 s |

Run your app against one: `cstudy dev --scenario kb=outage`. In a test, `setScenario` in your project's `tests/mockControl.ts` does the same.
