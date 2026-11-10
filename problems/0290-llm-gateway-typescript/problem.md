# LLM Gateway (TypeScript)

## Statement

A company's teams all use language models, and none of them talks to a provider directly. They call one internal gateway, which holds the keys, picks a provider, streams the answer back, keeps each team within its budget and records what each team spent.

Build that gateway, in levels. `cstudy` runs it in a Docker sandbox beside mock servers for two providers, and judges it by what it answers over HTTP and by what the providers saw it send. The company, the providers, their models, prices and answers are invented, and the providers' token counts are a stand-in: one token per word.

## Input

HTTP requests from the company's teams. `POST /v1/chat` comes first, and level 4 adds the routes for budgets and usage.

```json
{"messages": [{"role": "user", "content": "When do badges renew?"}], "stream": true, "max_tokens": 200}
```

| Part | Rule |
|------|------|
| `X-Team` header | The team that asks. Required |
| `messages` | The conversation, oldest first: a non-empty list, sent to a provider exactly as it came |
| `stream` | Optional: `true` asks for a stream, and anything else for a whole answer |
| `max_tokens` | Optional: a positive integer, the most tokens the answer may use. 256 when it is not given |

## Output

A whole answer is JSON, with `Content-Type: application/json`:

```json
{"provider": "primary", "content": "Badges renew every June.", "usage": {"prompt_tokens": 5, "completion_tokens": 4}}
```

A stream is `Content-Type: text/event-stream`, one event per piece of text as it arrives, then one with the provider and its usage, then `[DONE]`:

```text
data: {"delta":"Badges renew "}

data: {"delta":"every June."}

data: {"provider":"primary","usage":{"prompt_tokens":5,"completion_tokens":4}}

data: [DONE]

```

Each event is `data: `, its JSON, and a blank line, with the JSON written compactly, with no spaces, and its fields in the order shown, as `JSON.stringify` writes an object built in that order. The cases compare a stream's text exactly. `usage` holds the provider's two counts, under these names, whichever provider answered.

Every error is JSON, `{"error": "<message>"}`, with the status and message each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the gateway into `projects/llm-gateway-typescript/`, and `cstudy dev` runs it with its providers. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. `POST /v1/chat` already asks the primary for a whole answer.
- `src/primary.ts`: the primary's client, which only knows whole answers so far.
- `tests/`: your tests, run by `cstudy test`, with `tests/providerScenario.ts` to set a provider's visible scenario from a test.
- `vendors/<name>/API.md`: each provider's contract, for reading. Nothing depends on these copies.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings: each provider's URL and its fake key. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. The app has no network beyond its stack, and the keys reach no real provider. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To watch a failure yourself, run `cstudy dev --scenario primary=dropped_mid_stream` and ask with `curl -N`, which prints a stream as it comes.

## Level 1: Proxy and stream

Pass each request on to the primary provider, at `PRIMARY_LLM_URL`, documented in `vendors/primary/API.md`. Send `Authorization: Bearer <PRIMARY_LLM_KEY>` and the body `{"model": "brisk-1", "messages": ..., "max_tokens": ..., "stream": ...}`, always with all four fields: the caller's messages exactly as they came, its `max_tokens` or 256, and `stream` as `true` or `false`.

A whole answer is the primary's text and usage in the shape of the Output. A stream is what makes a gateway hard:

- **Send each piece as it arrives.** A caller watching a long answer should see its first words while the provider is still writing the rest, so nothing waits for the end of the stream. The primary's pieces are in `choices[0].delta.content`, and its usage comes in an event of its own near the end.
- **`[DONE]` means done.** Send it only after the primary's own `data: [DONE]`. A stream that stops without one did not finish, and a caller that receives `[DONE]` would take a broken answer for a whole one.
- **A broken stream ends with an error event**, and nothing after it:

```text
event: error
data: {"error":"the provider's stream ended early"}

```

| The primary | Your gateway |
|-------------|--------------|
| Ends its stream with `data: [DONE]` | Sends the usage event, then `data: [DONE]` |
| Closes its stream without `data: [DONE]` | Ends the stream with the error `the provider's stream ended early` |
| Sends an event whose data is not JSON | Passes none of it on, stops reading, and ends the stream with the error `the provider sent a malformed event` |
| Fails before your gateway has sent the caller anything: any answer but 2xx, or a stream that breaks before its first piece | 502, `{"error": "no provider answered"}`, in JSON: a stream that never started is no stream |

Until the first piece of text is ready, your gateway can still answer with any status, so it sends its own 200 and `text/event-stream` only then.

A wrong request is refused before any provider hears of it, in this order:

| Request | Status | Body |
|---------|--------|------|
| No `X-Team`, or an empty one | 400 | `{"error": "X-Team is required"}` |
| A body that is not a JSON object | 400 | `{"error": "the body must be a JSON object"}` |
| `messages` missing, empty or not a list | 400 | `{"error": "messages must be a non-empty list"}` |
| `max_tokens` given, and not a positive integer | 400 | `{"error": "max_tokens must be a positive integer"}` |

### Example 1

<!-- case: v1 -->

A whole answer: `POST /v1/chat` with `X-Team: search` and `{"messages": [{"role": "user", "content": "When do badges renew?"}]}` answers 200 with `{"provider": "primary", "content": "Badges renew every June.", "usage": {"prompt_tokens": 5, "completion_tokens": 4}}`, after one request to the primary with `"max_tokens": 256` and `"stream": false`.

### Example 2

<!-- case: v2 -->

The same question with `"stream": true` answers 200 with the stream of the Output, after one request to the primary with `"stream": true`.

### Example 3

<!-- case: v3 -->

The primary's stream sends its first event, then closes. The caller gets that piece, then the error, and no `[DONE]`:

```text
data: {"delta":"Badges renew "}

event: error
data: {"error":"the provider's stream ended early"}

```

## Level 2: Rate limits and timeouts

A provider can be busy, slow, or quiet in the middle of an answer. The request log of the mock server shows what your gateway really did.

| The primary | Your gateway |
|-------------|--------------|
| Answers 429 with `Retry-After` of 1 or 2 seconds | Asks again after waiting at least that long, up to 3 requests in all |
| Answers 429 with no `Retry-After` | Asks again after waiting at least 500 ms, counted in the same 3 |
| Answers 429 with a longer `Retry-After` | Gives up at once: your caller is waiting |
| Answers 5xx | Gives up, and does not ask again |
| Sends no status and headers within 1.5 s | Gives up on that request, and does not ask again |
| Does not finish a whole answer within 1.5 s | The same |
| Goes 1 s without an event, before its first event or between two | The stream has stalled: your gateway stops waiting for it |

The wait counts from the moment the 429 arrived. Giving up before the caller has had a piece of text is the 502 of level 1, and after it, a stream that stalled ends with the error `the provider's stream stalled`.

**A stream that has started is never asked again.** Once a piece of text has reached your caller, asking the provider again would start the answer over: the caller would read the first words twice. A stream that breaks after that point ends with its error event, whatever the reason.

A stream that keeps talking may take longer than 1.5 s in all: the 1.5 s is for the status and headers, and the 1 s is for the silence between events.

### Example 1

<!-- case: v4 -->

The primary answers 429 with `Retry-After: 1`, then streams: the caller gets the whole stream, after 2 requests to the primary at least a second apart.

### Example 2

<!-- case: v5 -->

The primary answers 429 with `Retry-After: 1` to everything: `POST /v1/chat` answers 502 with `{"error": "no provider answered"}`, after exactly 3 requests at least a second apart. The secondary is overloaded too, which matters from level 3.

### Example 3

<!-- case: v6 -->

The primary takes 2.5 s to answer a stream: 502 after 1.5 s, and one request to the primary. The secondary is overloaded too.

## Level 3: Fallback

The company has a second provider, at `SECONDARY_LLM_URL`, documented in `vendors/secondary/API.md`. It looks like the primary and differs in the details: its path, its key header, the name of its token limit, the names of its events, its end of stream, and an `error` event it can send inside a 200 stream.

When the primary gives up, by the rules of level 2, before any piece of text has reached your caller, your gateway asks the secondary instead: once, with `X-Api-Key: <SECONDARY_LLM_KEY>` and `{"model": "steady-2", "messages": ..., "max_output_tokens": ..., "stream": ...}`, the same messages and the same limit the primary was sent. The caller cannot tell which provider answered except by `"provider": "secondary"`: the same events, the same shape, the usage under the same names.

- **The same messages.** A fallback that trims, rewrites or adds to the conversation gives the caller an answer to a different question.
- **Never after the first piece.** Once a piece of text from the primary has reached your caller, the answer is the primary's, and a break ends it with an error event. Switching providers then would glue the start of one answer to another.
- **The secondary is the last one.** When it fails too, before any piece of text, the answer is 502 `{"error": "no provider answered"}`. Its `error` event counts as a failure, and after a piece of text it ends the stream with the error `the provider reported an error`. The timeouts of level 2 hold for it, and it is asked only once.

### Example 1

<!-- case: v7 -->

The primary answers 503: the caller gets the secondary's answer, after one request to each, with the secondary sent the same messages:

```text
data: {"delta":"Renewals happen "}

data: {"delta":"each June."}

data: {"provider":"secondary","usage":{"prompt_tokens":5,"completion_tokens":3}}

data: [DONE]

```

### Example 2

<!-- case: v8 -->

The primary's stream drops after its first event: the caller gets that piece and the error `the provider's stream ended early`, as at level 1, and the secondary hears nothing.

### Example 3

<!-- case: v9 -->

The primary answers 503 and the secondary's stream starts with an `error` event: 502 with `{"error": "no provider answered"}`.

## Level 4: Budgets and cost

Each team may have a budget in tokens, and the gateway keeps it from the usage the providers report, streamed or whole.

| Request | Status | Body |
|---------|--------|------|
| `PUT /v1/teams/<team>/budget` with `{"tokens": 1000}` | 200 | `{"team": "<team>", "budget_tokens": 1000}` |
| The same, when `tokens` is not a non-negative integer | 400 | `{"error": "tokens must be a non-negative integer"}` |
| `GET /v1/teams/<team>/usage` | 200 | `{"team": "<team>", "prompt_tokens": 10, "completion_tokens": 8, "cost_micros": 68, "remaining_tokens": 982}` |

- **What a team used** is the sum of `prompt_tokens` and `completion_tokens` of every answer it got, whichever provider answered, the usage of a stream included. A request that no provider answered, or that was refused, costs nothing.
- **What remains** is the budget less what the team has used, since the gateway started, and never less than 0. A new budget replaces the old one and counts what the team has already used. `remaining_tokens` is `null` for a team with no budget, which has no limit.
- **Capping.** Before asking a provider for a team with a budget, your gateway lowers the limit it sends to what remains: `max_tokens` to the primary, or `max_output_tokens` to the secondary, is the smaller of the caller's limit, 256 by default, and the remaining tokens.
- **Refusing.** A team with nothing left gets 429 `{"error": "token budget exhausted"}`, in JSON, stream or not, and no provider hears of it. One answer may pass the budget, since the prompt's tokens are known only after it: the next request is refused.
- **Cost** is recorded per team from the answering provider's prices, in millionths of a credit, `cost_micros`. A price is in credits per 1,000,000 tokens, so each token costs that many micro-credits, and every amount is a whole number:

| Provider | Model | Prompt tokens | Completion tokens |
|----------|-------|---------------|-------------------|
| primary | `brisk-1` | 2 | 6 |
| secondary | `steady-2` | 3 | 15 |

A team the gateway has not seen answers zeros, with `remaining_tokens` null.

### Example 1

<!-- case: v10 -->

The team `people` has a budget of 100 tokens and asks for `"max_tokens": 4096`: the primary is sent `"max_tokens": 100`.

### Example 2

<!-- case: v11 -->

The team `billing` has a budget of 1,000 and gets one streamed and one whole answer from the primary, each of 5 prompt and 4 completion tokens: `GET /v1/teams/billing/usage` answers `{"team": "billing", "prompt_tokens": 10, "completion_tokens": 8, "cost_micros": 68, "remaining_tokens": 982}`, since 10 × 2 + 8 × 6 is 68.

### Example 3

<!-- case: v12 -->

The team `legal` has a budget of 9 and a streamed answer used all 9: its next request answers 429 with `{"error": "token budget exhausted"}`, and the primary hears of it only once.

## Constraints

- A piece of text reaches the caller as soon as the provider sends it: the hidden cases include a stream that takes 2.5 s and one that goes quiet after its first event.
- At most 3 requests to the primary and 1 to the secondary for one request to your gateway, and none after a piece of text has reached the caller.
- A wait never comes up short: the hidden cases measure the gap between a 429 and your next request.
- A provider's 200 is not a finished answer: only its end of stream is.
- Your gateway reaches the providers only through `PRIMARY_LLM_URL` and `SECONDARY_LLM_URL`, and listens on all interfaces inside the container.

## Follow-ups

- A stream drops after half the answer, and its usage never came. What should the team be charged, and how would you estimate it?
- Two requests from one team run at the same time, each capped to the same remaining budget. How much can the team overspend, and what would a reservation of `max_tokens` change?
- The primary has failed for a minute. What would a circuit breaker change in the latency your callers see, and in the load on the primary when it recovers?
- The caller closes its connection halfway through a stream. What should happen to the request to the provider, and who pays for the tokens still coming?
- A provider caches the start of a prompt it has seen. What must stay the same between two turns of a conversation for that to work, and what in a gateway could break it?

## Hints

### Hint 1

Read the provider's body as a stream of bytes, not with `response.text()`, and split it into events on the blank line. One read can hold half an event, or several.

### Hint 2

Separate reading a provider from writing to your caller. A provider's client can turn its stream into the same small pieces, text or usage, whatever its format, and the code that writes to the caller only counts whether it has written anything yet.

### Hint 3

A timeout on the whole request cannot tell a slow answer from a stalled one. Race each read against a timer instead, and start a new timer for each one.

### Hint 4

Decide what to do with a failure by one question: has any piece of text reached the caller? Before, the request can still be retried, fall back or answer 502. After, the only honest end is an error event.
