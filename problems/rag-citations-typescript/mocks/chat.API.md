# The chat model

The team's language model, `help-chat-1`, behind a chat-completions API. It reads a conversation and answers it. Your app reaches it at `CHAT_URL`, with the key in `LLM_API_KEY`. This is its contract, and it will not change for you.

## `POST /v1/chat/completions`

Send the key as `Authorization: Bearer <key>`, and a JSON body with the model and the messages. A message's `content` is a text, or a list of parts, each `{"type": "text", "text": "..."}`:

```json
{"model": "help-chat-1",
 "messages": [{"role": "system", "content": "Answer the question using only the sources. ..."},
              {"role": "user", "content": [{"type": "text", "text": "[leave:1] the end of March. Ask your manager ..."},
                                           {"type": "text", "text": "Question: How much notice do I need before taking vacation?"}]}]}
```

It answers 200 with the model's reply in `choices[0].message.content`, a text:

```json
{"id": "chat-7", "object": "chat.completion", "model": "help-chat-1",
 "choices": [{"index": 0, "finish_reason": "stop",
              "message": {"role": "assistant", "content": "{\"answer\": \"Ask your manager at least two weeks ahead, through the leave calendar.\", \"citations\": [\"leave:1\"]}"}}],
 "usage": {"prompt_tokens": 96, "completion_tokens": 15}}
```

The reply is whatever the model wrote. Given the system prompt in `src/providers.ts`, it writes a JSON object with `answer` and `citations`, but nothing makes it: read it as text that should hold JSON, and check it. A model also cites what it likes, sources it was never shown included.

## This one is a stand-in

In the sandbox, `help-chat-1` is a stand-in with no model behind it. It knows the questions the cases ask, and finds the question by the last part of the user message, `Question: ` followed by the question exactly as the case sent it. It answers each with a fixed reply, as a model given the right sources would. Any other request answers 400:

```json
{"error": {"type": "unknown_question", "message": "help-chat-1 here is a stand-in that answers the questions the cases ask only, ..."}}
```

## When it fails

| Status | Meaning | Headers |
|--------|---------|---------|
| 429 | Too many requests: wait, then send the same request again | `Retry-After`: the whole seconds to wait |
| 5xx | Its own trouble | |

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `rate_limited_then_ok` | The first request answers 429 with `Retry-After: 1`, and every later one as usual |
| `invented_citation` | Asked how long customers have to ask for a refund, the model also cites `refunds:7` |

Run your app against one: `cstudy dev --scenario chat=invented_citation`. In a test, the helper in your project's `tests/` does the same.
