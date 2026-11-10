# The chat model

A chat model behind a generic chat-completions-style API, which your app reaches at `MODEL_URL` with the key in `MODEL_API_KEY`. It reads a conversation and the tools it is offered, and replies with a final answer or with calls it wants run. This is its contract, and it will not change for you.

In the sandbox the model is a stand-in that replies from a script. It chooses each reply by the conversation so far, so it answers the questions the cases ask, step by step, when your app sends the conversation as this page documents it. To any other conversation it replies with the final answer `No scripted reply matches this conversation.`

## `POST /v1/chat/completions`

Headers: `Authorization: Bearer <MODEL_API_KEY>` and `Content-Type: application/json`.

```json
{
  "model": "assistant-small-1",
  "messages": [
    {"role": "system", "content": "You are the help desk assistant of an online shop, ..."},
    {"role": "user", "content": "Where is order A-1042?"}
  ],
  "tools": [
    {"type": "function", "function": {"name": "lookup_order", "description": "Look up an order by its id.",
      "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "pattern": "^A-[0-9]{4}$"}},
                     "required": ["order_id"], "additionalProperties": false}}}
  ]
}
```

| Field | Meaning |
|-------|---------|
| `model` | The model's name, `MODEL_NAME` |
| `messages` | The whole conversation so far, oldest first. The model remembers nothing between requests |
| `tools` | The tools the model is told about. It can still name any tool in a reply: nothing in this API stops it |

### Messages

| Role | Fields | What it is |
|------|--------|------------|
| `system` | `content`: text | Your app's instructions, first and once |
| `user` | `content`: text | The question |
| `assistant` | `content` and `tool_calls`, as the model replied | A reply of the model's, sent back as it came |
| `tool` | `tool_call_id`, and `content`: text or any JSON value | The result of one call, whose id `tool_call_id` names. A JSON value reaches the model as data, marked as a tool's result |

After a reply with calls, the conversation goes on with that reply, then one `tool` message for each of its calls, in the order of the calls.

### Reply

200 with:

```json
{
  "id": "chat-1",
  "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
    "role": "assistant", "content": null,
    "tool_calls": [{"id": "call_fce0d7af", "type": "function",
                    "function": {"name": "lookup_order", "arguments": "{\"order_id\": \"A-1042\"}"}}]}}],
  "usage": {"prompt_tokens": 380, "completion_tokens": 22}
}
```

| Field | Meaning |
|-------|---------|
| `choices[0].message` | The reply. With `tool_calls`, the model wants those calls run and their results sent back. Without them, or with an empty list, `content` is its final answer |
| `tool_calls[].id` | The call's id, unique in the conversation |
| `tool_calls[].function.name` | The tool it wants. It may be one it was not offered, or one that does not exist |
| `tool_calls[].function.arguments` | The arguments, as JSON text the model wrote. It may not be JSON, or not what the tool's parameters say |
| `usage` | The tokens this request used: `prompt_tokens` read and `completion_tokens` written. Every reply has it |

## When it fails

| Status | Meaning |
|--------|---------|
| 429 | Too many requests |
| 5xx | Its own trouble, such as being overloaded |

## Scenarios

These change how the model answers. They are what you can try for yourself, and not all it can do.

| Name | What it does |
|------|--------------|
| `overloaded` | Every request answers 503 |

Run your app against one: `cstudy dev --scenario model=overloaded`. In a test, `setScenario` in your project's `tests/mockControl.ts` does the same.
