# The primary provider

The provider your gateway asks first. Your gateway reaches it at `PRIMARY_LLM_URL` with the key in `PRIMARY_LLM_KEY`. This is its contract, and it will not change for you.

## `POST /v1/chat/completions`

Send `Authorization: Bearer <PRIMARY_LLM_KEY>` and a JSON body:

```json
{"model": "brisk-1", "messages": [{"role": "user", "content": "When do badges renew?"}], "max_tokens": 256, "stream": false}
```

| Field | Meaning |
|-------|---------|
| `model` | `brisk-1`, the one model the gateway uses here |
| `messages` | The conversation, oldest first |
| `max_tokens` | The most tokens the answer may use |
| `stream` | `true` for server-sent events, `false` for one whole answer |

### A whole answer

```json
{
  "id": "chat-1",
  "object": "chat.completion",
  "model": "brisk-1",
  "choices": [
    {"index": 0, "message": {"role": "assistant", "content": "Badges renew every June."}, "finish_reason": "stop"}
  ],
  "usage": {"prompt_tokens": 5, "completion_tokens": 4}
}
```

### A stream

With `"stream": true` it answers `text/event-stream`: each event is one `data:` line and a blank line. The text comes in pieces, in `choices[0].delta.content`. A last event carries `usage` and no choices, and `data: [DONE]` ends the stream:

```text
data: {"id": "chat-1", "model": "brisk-1", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Badges renew "}}]}

data: {"id": "chat-1", "choices": [{"index": 0, "delta": {"content": "every June."}, "finish_reason": "stop"}]}

data: {"id": "chat-1", "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 4}}

data: [DONE]

```

A stream that ends without `data: [DONE]` did not finish, whatever it sent before.

| Field | Meaning |
|-------|---------|
| `usage.prompt_tokens` | The tokens of the messages it read |
| `usage.completion_tokens` | The tokens of the answer it wrote |

## When it fails

| Status | Meaning |
|--------|---------|
| 429 | Too many requests. `Retry-After` says how many whole seconds to wait, when it is there |
| 5xx | Its own trouble |

A slow answer is also possible, and so is a stream that goes quiet: it does not promise how long one takes.

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `rate_limited` | Every request answers 429 with `Retry-After: 1` |
| `rate_limited_then_ok` | The first request answers 429 with `Retry-After: 1`, and the next ones as usual |
| `outage` | Every request answers 503 |
| `slow` | Every request answers as usual, after 2.5 s |
| `dropped_mid_stream` | A stream sends its first event, then the connection closes |

Run your gateway against one: `cstudy dev --scenario primary=outage`. In a test, the helper in your project's `tests/` does the same.
