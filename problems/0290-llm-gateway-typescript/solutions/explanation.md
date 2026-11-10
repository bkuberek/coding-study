# LLM Gateway (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per event and per team | default answer: each provider's client turns its stream into the same small pieces, and the gateway commits to a provider when the first piece reaches the caller |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Stream an answer through, and end it honestly | `src/sse.ts`, which reads events as they arrive; `stream()` in `src/primary.ts`; `src/gateway.ts`, which writes each piece and ends with `[DONE]` or an error event; `src/requests.ts` for the refusals |
| 2 | Wait out a 429, and give up on what is slow or quiet | `waitBeforeRetry` and a bounded loop in the primary's client; `src/upstream.ts`, a clock for the status and headers; a timer per read in `src/sse.ts` |
| 3 | A second provider, never after the first piece | `src/secondary.ts` behind the same `Provider` interface, and a loop over providers in the gateway that stops at the first piece |
| 4 | Budgets and cost per team | `src/ledger.ts`: a budget, what was used, a price per model and the cap |

## Approach: reference (One stream reader per provider, a gateway that commits to a provider at the first event, and a ledger per team)

### Intuition

A stream changes what a failure means. Before the first piece of text has reached the caller, nothing has happened yet from the caller's side: the gateway can wait out a 429, ask another provider, or answer 502, and the caller sees one clean answer. After the first piece, the caller is reading an answer. Asking again would make it read the first words twice, and switching providers would glue one answer onto another. So the only honest end to a break is an error event, and never a `[DONE]`, which would pass a broken answer off as a whole one.

That single line, "has anything reached the caller?", decides every failure in the problem, so the code is built around it. Each provider's client hides its own format and gives back the same two kinds of piece, text and usage. The gateway only counts whether it has written a piece yet.

Streaming also needs a different kind of timeout. One limit on the whole request cannot tell a long answer that keeps talking from one that has gone quiet. So the gateway times two things: how long the status and headers take, and how long the stream goes between events.

### Say it out loud

"I read the provider's body as a stream, split it into events on the blank line, and write each piece to the caller as it arrives. I send `[DONE]` only when the provider sent its own end; a stream that stops early ends with an error event.

"Every failure turns on one question: has a piece reached the caller? Before that I can retry a 429 after its `Retry-After`, fall back to the second provider with the same messages, or answer 502. After it I can't do any of those without corrupting the answer, so I end the stream with an error.

"For timeouts I separate the wait for headers from the silence between events, since a total limit would cut a long healthy answer. And for budgets I record the usage from whichever provider answered, streamed or not, cap `max_tokens` to what is left, and refuse before calling anyone when nothing is."

### Algorithm

1. Refuse a wrong request first: no team, a body that is not an object, no messages, a bad `max_tokens`. Then, for a team with a budget, cap the limit to what remains, or refuse with 429 when nothing does.
2. For each provider in order, primary then secondary:
   1. Send the request. The primary waits out a 429 when its `Retry-After` is at most 2 s, or 500 ms without one, up to 3 requests. A status and headers must come within 1.5 s.
   2. A whole answer: read it within the same 1.5 s, record its usage and answer 200. Any failure moves on to the next provider.
   3. A stream: read events with a 1 s limit on each silence. If the stream fails before its first piece, move on to the next provider. At the first piece, send 200 and `text/event-stream`, and from then on write each piece as it arrives, record the usage when it comes, and end with `[DONE]` at the provider's end, or with an error event at a break.
3. No provider answered: 502.

### Design

- `src/server.ts`: the routes, and the step from a request to a capped `Ask`; the caller's connection closing aborts the request to the provider.
- `src/requests.ts`: `chatRequest` and `budgetTokens`, the refusals in the order the statement gives them.
- `src/provider.ts`: the seam: `Provider`, `Piece`, `Answer`, `ProviderFailure` and the messages of the error events.
- `src/upstream.ts`: one request with a clock on its status and headers, which a whole answer keeps running through its body and a stream stops at once.
- `src/sse.ts`: `serverSentEvents`, which yields each event once its blank line has arrived, half an event or several per read, and gives up after 1 s of silence.
- `src/primary.ts`: the primary's shape, `[DONE]`, and `waitBeforeRetry`, a pure function a test calls.
- `src/secondary.ts`: the secondary's path, key header, limit name, named events, `end` and `error`.
- `src/gateway.ts`: the loop over providers, `firstPiece`, which says whether the next provider may still answer, and `#relay`, which owns the stream once it has started.
- `src/ledger.ts`: `TeamLedger` and `PRICES`: budgets, usage, cost and the cap.

Not graded, and worth discussing:

- **A circuit breaker.** After a run of failures, skip the primary for a while and go straight to the secondary, so that an outage costs callers neither the 1.5 s timeout nor three requests' worth of waiting.
- **Reserving the budget.** Two requests from one team at the same time each see the same remaining tokens, so the team can pass its budget by up to one `max_tokens` per request in flight. Reserving `max_tokens` when a request starts, and settling it with the real usage at the end, closes that gap.
- **A stream with no usage.** A stream that breaks before its usage event costs the team nothing here, which is generous. Charging for the pieces sent, estimated from their length, is closer to what the provider will bill.
- **Heartbeats.** Many gateways send an SSE comment line every few seconds, so that a proxy between them and the caller does not close a quiet connection.

### Correctness

Every byte the caller receives was written after the provider sent it, because the reader yields an event as soon as its blank line arrives and the gateway writes it at once. `[DONE]` is written only after the provider's own end of stream returns from its client, and every other way out of the relay writes an error event, so a broken stream can never end with `[DONE]`. The gateway moves to another provider only from `firstPiece`, which runs before anything is written, so no fallback or retry can follow a piece the caller has seen. Retries happen inside the primary's `#opened`, before a stream is open, and are bounded by its counter. The messages go to each provider as the same parsed value, so a fallback cannot change them. Usage is recorded where each piece of usage is written or each whole answer returned, from the provider that sent it, so a streamed answer counts as a whole one does, and a request that fails or is refused records nothing.

### Complexity

- Time: per request — at most 3 requests to the primary and 1 to the secondary, and one pass over each event as it arrives
- Space: per event and per team — the bytes of one event not yet complete, and four numbers per team

### Trade-offs

Writing each piece as it comes means committing early: once a piece is out, a stalled provider cannot be replaced, and the caller gets an error where a buffered gateway could have quietly fallen back. That is the right trade for a chat answer, where seeing the first words fast is the point, and the wrong one for a batch job that only wants a complete answer, which should ask for a whole answer instead.

The primary's client retries and the secondary's does not, which keeps the worst case for a caller near 2 s of waiting plus one request to each provider. A shared retry helper would save a few lines and tie together two providers whose rules differ.

The pieces are a deliberately small shape, text or usage. A real gateway would carry tool calls, finish reasons and several choices, and the seam would grow with them; the point is that each provider's format stops at its client.

`node:http` and `fetch` keep the install small, and `fetch` gives the body as a stream, which is all the reader needs. An SSE library would parse the events, and the timing of silences would still be the gateway's own.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Buffers the whole stream with `await response.text()` and sends it at the end | The caller sees nothing until the provider has finished, and a stalled provider loses the pieces already sent: under a limit on the whole request, a healthy 2 s stream is cut too | `h14`: `first body byte after 2050 ms, expected within 1000 ms`, the same bytes sent too late; `h13`, `h23`: the body, and `secondary: expected 0 requests, saw 1` when the gateway falls back, thinking nothing was sent |
| Retries a stream that broke after it started | The caller reads the first words twice | `v3`, `h12`, `v8`: `"Badges renew "` twice, and `primary chat-stream: expected 1 request, saw 3` |
| Sends `[DONE]` whenever the provider's connection closes | A dropped stream looks like a whole answer | `v3`, `h7`, `h25`: the body |
| Passes on an event that is not JSON | The caller's parser breaks on it, and the gateway's record of usage with it | `h7` |
| Answers a 429 with its own fixed wait, or none | The provider said how long | `v4`, `h9`: `expected at least 950 ms from response 1 to request 2` |
| Waits however long `Retry-After` says | The caller waits 3 s for one request | `h11`, `h22`: `expected 1 request, saw 2` |
| Retries a 5xx or a timeout | More load on a provider that is already failing, and more waiting | `h15`, `h16`, `v6`: the count |
| One timeout on the whole request | Cannot tell a long healthy stream from a stalled one | `h14`, and `h13` without a silence limit |
| No timeout at all | A stalled or slow provider holds the caller until the case's limit | `v6`, `h13`, `h17` |
| Falls back after a piece reached the caller | The caller gets the start of one answer and the whole of another | `v8`, `h23`: `secondary: expected 0 requests, saw 1` |
| A fallback that rebuilds the conversation, such as dropping the system message | The secondary answers a different question | `v7`, `h18`, `h26`: `body messages the same as primary` |
| Sends the primary's body to the secondary unchanged | `max_tokens` means nothing to it | `v7`, `h26`, `h31`: `max_output_tokens` |
| Takes the secondary's 200 for success | Its `error` event arrives inside a 200 | `v9` |
| Records usage only from whole answers | A team that streams has no budget | `h28`, `v11`, `h34` |
| Caps `max_tokens` at the budget, not what remains | A team that has used most of its budget asks for all of it again | `h28`, `h39` |
| Checks the budget after the provider answered | The provider was called, and paid, for a refused request | `v12`, `h35`: `expected 0 requests` |
| Lets `remaining_tokens` go negative | An answer can pass the budget, and what remains is still 0 | `h36` |

**Edge cases.**

- One read can hold half an event, or the usage event and `[DONE]` together: split on the blank line, and keep what is left for the next read.
- A provider's first event can be malformed or never come: nothing has reached the caller, so that is still a fallback (`h24`, `h19`, `h20`).
- Until the first piece is ready, no headers go out, so a stream that fails before then can still be a plain 502 in JSON (`h8`, `v9`).
- The wait after a 429 counts from when the 429 arrived, not from when the request was sent.
- The usage event's JSON is built in the documented order, `provider` then `usage`, since the cases compare a stream's text exactly; `usage` is rebuilt from the provider's counts, so the secondary's `input_tokens` become `prompt_tokens`.
- A new budget counts what the team has already used (`h39`), and a budget of 0 refuses the first request (`h35`).
- A request no provider answered, or one the budget refused, costs nothing (`h32`, `h33`).
