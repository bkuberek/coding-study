# The secondary provider

The provider your gateway asks when the primary cannot answer. Your gateway reaches it at `SECONDARY_LLM_URL` with the key in `SECONDARY_LLM_KEY`. Its API looks like the primary's and differs in the details. This is its contract, and it will not change for you.

## `POST /v1/messages`

Send `X-Api-Key: <SECONDARY_LLM_KEY>` and a JSON body:

```json
{"model": "steady-2", "messages": [{"role": "user", "content": "When do badges renew?"}], "max_output_tokens": 256, "stream": false}
```

| Field | Meaning |
|-------|---------|
| `model` | `steady-2`, the one model the gateway uses here |
| `messages` | The conversation, oldest first, in the same form as the primary's |
| `max_output_tokens` | The most tokens the answer may use |
| `stream` | `true` for server-sent events, `false` for one whole answer |

### A whole answer

```json
{
  "id": "msg-1",
  "model": "steady-2",
  "output": {"text": "Renewals happen each June."},
  "usage": {"input_tokens": 5, "output_tokens": 3}
}
```

### A stream

With `"stream": true` it answers `text/event-stream`, and every event has a name. `delta` events carry the text in pieces, a `usage` event the tokens, and an `end` event ends the stream:

```text
event: delta
data: {"text": "Renewals happen "}

event: delta
data: {"text": "each June."}

event: usage
data: {"input_tokens": 5, "output_tokens": 3}

event: end
data: {}

```

A stream that ends without its `end` event did not finish.

| Field | Meaning |
|-------|---------|
| `usage.input_tokens` | The tokens of the messages it read |
| `usage.output_tokens` | The tokens of the answer it wrote |

## When it fails

| Answer | Meaning |
|--------|---------|
| 5xx | Its own trouble, such as being overloaded |
| An `error` event inside a 200 stream | It started to answer, then could not: `{"code": "overloaded", "message": "Try again later."}`. Nothing after it is part of an answer |

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `overloaded` | Every request answers 503 |
| `error_event` | A stream answers 200, then sends an `error` event as its first event and ends |

Run your gateway against one: `cstudy dev --scenario primary=outage --scenario secondary=overloaded`.
