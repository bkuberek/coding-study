# Tool-Calling Agent Loop (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per question | per question | default answer: judge every call the model asks for through fixed checks, wrap what tools answer as data, and count every reply against a budget |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Run the calls the model asks for, until it answers | The loop in `src/agent.ts`; `CallJudge` in `src/calls.ts` with `unknown_tool` and `invalid_arguments`; `problemsWith` in `src/schema.ts` |
| 2 | Only the caller's tools | `mayUse` in `src/roles.ts`: the offered list is filtered by role, and every call is checked against it |
| 3 | What tools answer is data | The `untrusted` envelope; `not_requested` for a refund of an order the question does not name; the canary check on arguments and on the final answer |
| 4 | Stop within budget, and survive failures | `Budget` in `src/budget.ts`; `runTool` turns any failure into `tool_error` or `tool_timeout`; the `repeated` check; `ModelUnavailable` becomes 502 |

## Approach: reference (The model proposes, the runtime decides: every call judged, every reply counted)

### Intuition

Loan Extraction Review (`0276`) taught one rule about a model's output: the model proposes, code validates. There the output was data, and the worst a wrong value could do was wait for a person. Here the output is actions. A tool call the runtime runs moves money, opens tickets and reads customer records, so the same rule moves from "check the values" to "check every call before it runs". The model is a component that can be wrong in any way, and it can be steered by anyone who writes text it reads.

That gives the runtime three questions to answer for each call, in an order where each answer is cheap and cannot be argued with. Is it a call at all: a tool that exists, with arguments its schema accepts? Is it this caller's call: a tool the caller's role may use? Is it what the caller asked for: a refund of the order they named, and nothing carrying the system prompt out? Only then does it run. None of those answers depends on anything the model or a tool said, which is the point: an attacker can write any text into a help center comment, but cannot change the caller's role, the question, or the canary.

Prompt injection is the reason the third question exists. The model reads tool results, and some of them were written by strangers. Telling the model to ignore instructions in tool output helps, and the system prompt does say so, but it is a request, not a control. So the runtime does two things. It keeps untrusted text where it belongs, inside a tool message, wrapped and marked, never in the system or user message where it would carry the weight of an instruction. And it makes sure that a model that is fooled anyway can do nothing the caller could not have asked for.

Then there is cost. A model can loop: ask for one more search, repeat a call it already has, or keep going because a tool keeps failing. Each step is a paid request. A budget in steps and tokens makes the loop end whatever the model does, and failures become results the model can read, so one broken tool costs a step rather than the whole question.

### Say it out loud

"The model only ever proposes. My loop sends the conversation and the tools, and when a reply asks for calls I judge each one: does the tool exist, may this caller use it, are the arguments valid against its schema, and for a refund, did the person name that order. Anything that fails is answered with an error the model can read, and never reaches a system.

"Tool results are data from outside, some written by strangers, so they go back only in tool messages, wrapped with a marker that says untrusted. The system prompt and the tool list never change mid-conversation, so nothing a tool says can grant a permission. The system prompt carries a canary; if it shows up in a call's arguments or the final answer, the prompt is leaking, and I withhold it.

"Finally, budgets. Every reply counts a step and its tokens. If the model still wants tools after six requests, or once the tokens are spent, I stop with a clear note and don't run calls nobody will read. A tool that fails or times out becomes an error result, and a call identical to one already run is refused, so a stuck model burns budget, not my systems."

### Algorithm

1. Filter `TOOLS` by the caller's role, once. Start the conversation with the system prompt and the question.
2. Send the conversation and the filtered tools to the model, and count the reply's step and tokens. A failed request, or a body that is not a reply, ends the question with 502.
3. A reply with no calls is the answer: withheld when it holds the canary, returned otherwise.
4. A reply with calls, when `MAX_STEPS` requests have been sent or the tokens have reached `TOKEN_BUDGET`, ends the question with a stop note, its calls not run.
5. Otherwise append the reply, then for each call append one tool message, decided by the first check that fails: `unknown_tool`, `not_allowed`, `invalid_arguments`, `not_requested`, `withheld`, `repeated`. A call that passes runs within `TOOL_TIMEOUT_MS`, and its answer goes back wrapped as untrusted data, or `tool_error` or `tool_timeout` when it fails.
6. Go back to step 2.

### Design

- `src/server.ts`: the routes, as a lookup that answers 404 and 405 in one place, the request check that answers 400, and the mapping of `ModelUnavailable` to 502. Everything else is `runAgent`'s.
- `src/agent.ts`: `runAgent`, the loop: the offered tools, the conversation, one `Budget` and one `CallJudge` per question, and the three ways it ends.
- `src/calls.ts`: `CallJudge.answer`, the checks of a call in their order, each returning its outcome and the content of its tool message. It holds the set of calls already run, by tool and canonical arguments, and `NAMED_IN_QUESTION`, the argument of a money-moving tool that must come from the question.
- `src/schema.ts`: `problemsWith`, a validator for exactly the keywords the tools use, which names each problem so the model can correct its next call.
- `src/roles.ts`: the roles and `mayUse`, the allowlist as data.
- `src/budget.ts`: `Budget`, the steps and tokens spent, and `exhausted`, which says why no further request may be sent.
- `src/model.ts`: `chat`, which checks that a reply is one the API documents, usage included, before anything reads it.
- `src/tools.ts`: `TOOLS`, now with the request each tool makes rather than a `run` that throws, and `runTool`, which never throws.
- `src/prompt.ts`: unchanged from the starter.

Not graded, and worth discussing:

- **A person in the loop.** An admin's assistant can still be steered to refund the order the admin named, for any amount up to the schema's maximum. Production agents ask a person to confirm actions that move money or speak for the company, show exactly what will run, and run only what was confirmed.
- **The model's own failures.** The reference does not retry a model that answers 429 or 503, and sets no timeout on it. A real service would retry with backoff within the question's budget, and give each request a deadline.
- **Writes across questions.** The `repeated` check lives for one question. Asking twice for the same ticket opens two. An idempotency key derived from the conversation, sent to the helpdesk, would make a retried write safe.
- **Telling the model how much is left.** Each request could set `max_tokens` from what is left of the budget, so one long reply cannot overshoot it.
- **A quarantined reader.** A stronger design hands untrusted text to a second model with no tools, which may only return a value in a fixed shape, and never shows the raw text to the model that can act.
- **Prompt caching.** Providers cache the longest unchanged prefix of a conversation. Never rewriting what was sent is what lets that work, which is why level 1 asks for a conversation that only grows.

### Correctness

A call reaches `runTool` only from the end of `CallJudge.answer`, after every check passed, so no call that names an unknown tool, a tool of another role, invalid arguments, an order the question lacks, or the canary reaches a system. The role and the question are set by the request and read only by those checks, and the offered tools are computed once before the first request, so nothing a tool answers can change what is allowed. Tool output is added to the conversation in one place, wrapped, inside a tool message, and earlier messages are never touched, so the system message and tools are the same in every request. `Budget.spend` runs after every reply and `exhausted` before any call of a reply runs, so no more than `MAX_STEPS` requests are sent, and no call runs once the budget is spent. `runTool` catches every failure, and `chat` checks the reply before it is read, so a tool can never make the question fail, and a broken model reply fails it with 502, never 500.

### Complexity

- Time: per question — at most `MAX_STEPS` model requests, each sending the whole conversation so far, and one check per call that is linear in its arguments
- Space: per question — the conversation, the calls listed and the set of calls run, all dropped when the question is answered

### Trade-offs

The checks are deterministic code, not a second model asked whether a call looks safe. They cannot be talked out of a decision, and their result is the same on every run, which a grader and an auditor both need. They also cannot catch what they do not test: an admin's refund of the right order for the wrong amount passes them all.

The canary is cheap and has no false positives, since nothing else ever writes it. It only catches verbatim leaks: a summary or a translation of the prompt passes. Keeping secrets out of the system prompt matters more than catching leaks of it.

Stopping without running the last reply's calls wastes the tokens of that reply. Running them would cost side effects, a ticket opened or a refund issued, whose results nobody would read.

Refusing a repeated call, rather than answering it again from the first result, keeps the rule simple and tells the model it is stuck. Answering from a cache would help a model that forgot a result, and hide one that loops.

`node:http` and the global `fetch` keep the install to the type checker. A framework or an agent library would hide the loop, which is exactly what this problem is about.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden or visible case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Runs every call the model asks for | Invalid arguments, other roles' tools and planted refunds all reach a system | Every level: `h1` answers 500, `v3`: `orders: expected 0 requests, saw 1`, `h12`: `helpdesk: expected 0 requests, saw 1` |
| `JSON.parse` on the arguments with no catch | Text the model cut short throws, and the question answers 500 | `h1`: `status: expected 200, got 500` |
| Checks the arguments are JSON, not their schema | `{"order_id": 1404}` reaches the order system | `h3`: `orders: expected 1 request, saw 3`, and `h4`, `v2` |
| Answers a refused call with no tool message, or one without the call's id | The model never hears why, and the conversation is not the one the API documents | `v2`, `h1`, `h3`: `model with body ...: expected 1 request, saw 0`, and the scripted model answers `No scripted reply matches this conversation.` |
| Offers only the caller's tools, and runs whatever is asked | The model names tools it was never offered, and planted text names them for it | `v3`, `h7`, `h10`, `v5`: `orders: expected 0 requests, saw 1` |
| Checks only `issue_refund` | A trainee's lookup or ticket runs | `h7`, `h10` |
| Offers every tool to every role | The model is told of tools it may not use | `v3`, `h7`, `h10`: `model with body {"tools": ...}: expected 2 requests, saw 0` |
| Reads a refused tool's arguments first | Refuses as `invalid_arguments` what is `not_allowed` | `h8`: `body.calls[0].outcome: expected "not_allowed", got "invalid_arguments"` |
| Calls a tool there is not `not_allowed`, or the reverse | The two outcomes mean different things to whoever reads the trace | `h2`, `h7` |
| Sends a tool's answer as a user message, or adds it to the system prompt | Gives text from strangers the weight of an instruction | `v5`, `h11`: the envelope and `body_same_as` assertions, and the scripted model answers `No scripted reply matches this conversation.` |
| Sends a tool's answer unwrapped | The model cannot tell where data ends | `v5`, `h11`: `model with body ...: expected 1 request, saw 0` |
| Edits or drops planted text | Hides from the model what the data said, and protects nothing the checks do not | `h11` |
| Relies on the role alone for refunds | An admin's assistant refunds an order only a comment named | `h13`: `body.calls[1].outcome: expected "not_requested", got "ok"` |
| Refuses every write once untrusted text was read | The admin's own refund of the order they named is refused | `h14` |
| Checks the canary in the answer only | A ticket carries the prompt out | `h12`: `helpdesk: expected 0 requests, saw 1` |
| No canary check | The prompt goes back to the staff member | `v6`, `h15`: `body.stop: expected "withheld", got "answered"` |
| No step limit | A model that never answers loops until the token budget, or the hang guard, stops it | `v8`: `body.stop: expected "step_limit", got "token_budget"`, `model: expected 6 requests, saw 12`, and `h22` |
| Runs the last reply's calls, then stops | Side effects nobody reads | `v8`: `kb: expected 5 requests, saw 6`, and `h16` |
| `>` for the budget | A budget spent exactly is not spent | `h17` |
| Throws away a final answer past the budget | The tokens are spent either way, and the answer is lost | `h18`: `body.stop: expected "answered", got "token_budget"` |
| Stops one step early | The sixth request is allowed, and its answer is the answer | `h25` |
| Lets a tool's failure throw | One broken system fails the whole question | `v7`, `h20`, `h21`: `status: expected 200, got 500` |
| No timeout on tools | The question waits as long as the slowest system | `h19`: `body.calls[0].outcome: expected "tool_timeout", got "ok"` |
| No repeat check, or a check on the raw argument text | A stuck model hammers a system, or opens the same ticket twice | `h22`: `orders: expected 1 request, saw 5`, `h23`: `helpdesk: expected 1 request, saw 2` |
| Answers 500 when the model fails | A failure of the model is not a bug in the request | `h24`, `h26` |

**Edge cases.**

- One reply can ask for several calls. Each gets its own tool message, in order, and one being refused does not stop the next (`h3`, `h9`).
- Arguments can be valid JSON and still not an object: a list or a number is `invalid_arguments` (`h4`).
- An admin may use every tool, but a tool that does not exist is still `unknown_tool` (`h2`).
- A planted instruction can claim the caller's role has changed. The role came with the request and nothing else sets it (`h11`).
- The canary is checked on the parsed arguments, so escaping characters in the JSON text does not hide it (`h12`).
- The step limit and the budget are checked only on a reply that asks for calls, so a final answer at the sixth step, or past the budget, is still the answer (`h18`, `h25`).
- A body that is not JSON under a 200 is a failure like a 503, for a tool (`h21`) and for the model (`h26`).
- `{"order_id":"A-4120"}` and `{"order_id": "A-4120"}` are the same call, and so are two objects with the same keys in another order (`h22`, `h23`).
