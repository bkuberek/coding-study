# ADR 0029: The AI foundation: one model port, four providers with your own keys, consent and a daily cap, and AI review of rubric problems

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-16 |
| Spec | [ai](../specs/ai.md); [cli](../specs/cli.md#cstudy-ai), [web-ui](../specs/web-ui.md#ai-preview), [progress-and-scheduling](../specs/progress-and-scheduling.md#schema), [compatibility](../specs/compatibility.md#checked-by) |
| Amends | [ADR 0021](0021-ai-reviewed-problems.md): its steps 1 and 2 (the provider port and keys; written answers on rubric problems) are designed here. R1 to R8 and R11 are settled as below; its `ReviewProvider` port becomes a use case on one model port; `cstudy ai review` replaces the suggested `cstudy ai-review`; R8's labeled answer sets wait for a later milestone |
| Builds on | [ADR 0015](0015-local-web-ui.md) (jobs), [ADR 0022](0022-settings-and-reset.md) (the config description and Settings), [ADR 0027](0027-compatibility-contract.md) (preview surfaces and public records) |

## Context

The roadmap's milestone v0.54 opens the AI preview of 1.0 with criteria AI1 (your own keys, consent, a daily cap, usage and known cost), AI2 (fixed or tiered routing), AI3 (AI review of rubric-checked problems) and AI8 (with AI off, nothing leaves the machine), and a Settings section. The chat drawer (v0.55) and problem sessions (v0.56) build on what this milestone lays down.

The owner settled the rules: you bring your own key; keys live only in `credentials.toml`, never in the workspace, logs, transcripts or exports; nothing is sent before your consent per provider, model and purpose; a daily token cap; usage and the known cost shown; four provider adapters behind a model port; one fixed model, or auto routing over a fast and a strong tier you configure; AI review returns a schema-validated verdict per rubric criterion, stored as a versioned record with provider, model and rubric version, labeled AI review, never changing a grade or the schedule; and with AI off, nothing leaves the machine and every other feature works as before, proven by a test. For the later milestones the owner also settled that help caps the review grade, that an untagged turn counts as light help, that exports leave transcripts out unless asked, that a mock allows the interviewer mode only, and that a free session during an attempt is allowed with a reminder. Nothing here contradicts them; the foundation leaves room for them (purposes, record tables, the export rule).

What exists today:

- No command uses the network after installs, except the downloads of `cstudy doctor --fix`, made with the standard library's `urllib.request` (`adapters/language_servers/lsp_directory.py`).
- `config.toml` is per user and travels in dotfiles; `progress.db` is per workspace, migrated forward after a backup ([compatibility](../specs/compatibility.md#migrations)).
- Rubric problems (`system-design`, `code-review`) have a `rubric.md` of areas and `- [ ] <criterion>` lines (`domain/rubric.py`), and your answer is the notes file `notes/<track>/<slug>.md`. Their grade is your own rating; revealing the rubric and the reference never lowers it.
- `checked_by` reserves `ai-review` for this milestone.
- `cstudy serve` runs use cases on one worker thread, one at a time, and long work in child `cstudy` processes: runs and jobs.

An earlier design draft (2026-11-14), which the owner delegated to the assistant's judgment, is the starting point. This ADR keeps its single model port, its keys and consent shapes and its review record, and changes four things, each with its reason below: no cost estimates from prices, AI requests from the page run as jobs, the usage log and consents stay out of exports, and the check task is added so routing is observable from the start.

## Decision

### One model port

Every request to a provider goes through one application port, `LanguageModels`: `complete(request)` answers a request whole, with structured output when the request names a schema, and `list_models(provider)` lists a provider's model ids. ADR 0021's `ReviewProvider` becomes the review use case on this port: tasks differ in their instructions and their schema, not in their transport. The chat milestone adds streaming to the same port.

### Four providers

| Provider | API it speaks | Why |
|----------|---------------|-----|
| `anthropic` | The Messages API | Owner's list (ADR 0021 O2) |
| `openai` | The Responses API | Owner's list |
| `google` | The Gemini API with an API key (`generateContent`) | Owner's list; Vertex AI and its service accounts are out of scope |
| `openrouter` | Chat Completions | Owner's list. One key reaches many vendors' models, open-weight ones included, and it reports each request's cost |

A local model is not a fourth provider now: the roadmap puts it after 1.1. When it comes, it is the OpenRouter adapter's Chat Completions with another base URL and no key, which Ollama, LM Studio and llama.cpp's server speak too.

Each adapter asks for structured output the way its API documents it, and the domain checks every reply again. The schema sent to a provider uses only the subset all four accept: objects with every property required and `additionalProperties: false`, arrays, strings, string enums and booleans. Lengths, counts and anything else a provider might not enforce are the domain's checks.

### HTTP through the standard library

The adapters send JSON over HTTPS with `urllib.request`, TLS from `ssl.create_default_context()`, the proxy variables urllib honors, a deadline per task and no automatic retry.

| Option | Why not |
|--------|---------|
| The providers' SDKs | Four packages to track, which bring pydantic (a compiled wheel) and httpx with its own dependencies, for an opt-in preview. The runtime dependencies reach the Homebrew formula through a hashed requirements file ([ADR 0013](0013-homebrew-distribution.md)), and each new one is a review and a supply-chain cost |
| httpx alone | Four or five more packages for what `urllib.request` already does: JSON bodies, headers, timeouts, proxies, and reading a stream line by line, which the chat milestone needs |

The cost of this choice is four request shapes of our own. Recorded responses of each provider pin them in the tests, and a provider that changes its API breaks the preview until the next release.

### Keys in `credentials.toml`

As ADR 0021 R2 and O5 set it: `credentials.toml` in the directory of `config.toml`, one table per provider with `api_key`, created with mode `0600` and rewritten whole, atomically, by `cstudy ai key` and Settings. Keys are never read from environment variables.

| Rule | How it holds |
|------|--------------|
| Never in the workspace | `cstudy` refuses to read or write the file when it would be inside the workspace, as a `CSTUDY_CONFIG` inside it would put it. `cstudy doctor` warns when the file is inside a Git repository |
| Never in output, logs or records | A key is held in a value whose text is `<key>`, and only an adapter unwraps it, into a request header. Text a provider sends back has the key replaced by `<key>` before it reaches a message. `progress.db`, exports, `--json` documents and the web API never hold it; a test with a sentinel key searches all of them |
| Never handed on | No child process gets a key in its arguments or environment: the child `cstudy ai` reads the file itself. Runners, language servers and containers never get it; the language-server broker refuses the file as a library file. User code of a problem that runs natively runs as you and could read it, which ADR 0021 accepted |
| The page | Sends a key once, in the body of a write to the loopback server, and never gets one back: the API answers only whether a key is set |

### Consent

Nothing is sent to a provider's model for a purpose before you agree to it: one consent per provider, model and purpose, recorded in `progress.db`. The question shows the provider and the model, each item that will be sent with its size, the estimated tokens and today's usage, and says that your provider account's terms apply. You answer it at a terminal, in the page's dialog, or with `cstudy ai consent`, never with a `--yes`. You can revoke it at any time, after which `cstudy` asks again. The purposes of this milestone are `review` and `check`; later milestones add theirs.

Listing a provider's models is not a send: it carries nothing of yours, counts no tokens and needs no consent, and it runs only when you ask, with AI on.

Consents and usage belong to the workspace whose `progress.db` holds them, beside the progress whose content they send. A second workspace asks again and counts its own cap. A store per user would be a new file with its own migrations and backups, for a difference only someone with two workspaces sees.

### Usage, the daily cap and the known cost

Every request is a row of `ai_calls`: purpose, provider, model, tier, the tokens the provider reported, the tokens the cap counts, the cost when the provider reported one, and the outcome. The cap, `ai.daily_token_cap` (500,000 by default), counts input and output tokens of every purpose per local day, in the workspace. A request is refused before it leaves when today's counted tokens and its estimate (its text in bytes divided by 4, plus its output limit) would pass the cap; a request whose reply reported no usage counts its estimate. The cap cannot be turned off; it can be set as high as you like.

The known cost is the cost a provider reports, which today only OpenRouter does, in US dollars. `cstudy` ships no price table and takes no prices from you, which the draft proposed: prices change without notice, and a wrong cost is worse than tokens with `cost unknown`. AI1 asks for the known cost, and the tokens are always shown.

### Routing

`ai.routing` is `fixed` (the default), where every task uses `ai.model`, or `auto`, where each task uses the tier the domain's task table names, `ai.fast` or `ai.strong`. Each is `<provider>:<model id>`; `cstudy` names no model of its own (ADR 0021 R4), and `cstudy ai models` lists a provider's ids. A task whose model is unset, or whose provider has no key, is refused with what to set; there is no fallback to another model. This milestone's tasks: AI review uses the strong tier; the check, `cstudy ai check`, sends a fixed message to every model the routing names, so each tier can be seen working before it is used.

### AI review

| Item | Decision |
|------|----------|
| Problems | The rubric problems, `system-design` and `code-review`. Not the `lld` problems' design rubrics: their answer is code, and ADR 0021 rejected a model judging code |
| When | On the problem's attempt in progress, or its latest attempt once it ended, while its notes differ from the template. Locked while a mock runs, as `cstudy solution` is |
| Sent | Versioned instructions, the problem's prompt and, for a code review, its change, the rubric's criteria numbered `C1` to `Cn`, and your notes as data. Never `reference.md`: the rubric names what a strong answer covers, and the reference would push the review toward one design |
| Reply | Per criterion a verdict, `met`, `partial` or `missing`, up to three quotes from your notes as evidence, and the gaps; then a summary. A quote not found in the notes is dropped and counted. A reply that misses a criterion is refused, and nothing is stored |
| Record | `ai_reviews`, format 1, a public record: provider, model, instructions version, the SHA-256 of `rubric.md` as the rubric version, the SHA-256 of the notes reviewed, each criterion's text and verdict, the summary, the usage, and when it was dismissed. It reads the same after the rubric changes |
| Honesty | Labeled AI review everywhere, with `The same answer can get a different review.` It never finishes an attempt and never changes a grade, the schedule, `cstudy stats` or a status. You can review again and dismiss a review |
| Checked by | The rubric kinds gain `ai-review`, described by the problem whatever your settings, as the roadmap's E3 planned the column |

### Where requests leave from

In the terminal, the `cstudy ai` command's own process sends. In the page, an AI action is a job: the server checks in-process what the command would refuse, asks for consent through the API's confirmation, and then starts the child `cstudy ai …`, which sends. The server process never sends to a provider, so its one worker never waits on one, its CSP does not change, and an AI request gets a job's Cancel and lines. A review shares the one job slot, so it waits for a running `doctor --fix`, and the other way round.

### With AI off, nothing leaves the machine (AI8)

| Layer | Guarantee |
|-------|-----------|
| Settings | `ai.enabled` is false by default |
| One door | Only the adapters in `coding_study.adapters.ai` reach a provider. The import contracts forbid `http`, `socket` and `ssl` in the domain and application layers, and the entrypoints import nothing of `coding_study.adapters.ai` |
| Construction | With AI off, the environment's model port refuses every request and the provider adapters are never imported; with AI on, they are imported at the first request, so no other command pays for them |
| Refusal first | Every use case that sends checks `ai.enabled` before anything else |
| Tests | Every fast test runs under a guard that refuses a connection or a name lookup off the loopback; the AI-off tests run each `cstudy ai` command and each AI job with a sentinel key and AI off, and see each refused with no connection attempted, nothing of `coding_study.adapters.ai` imported, and the key nowhere in their output |

The visible differences with AI off are the Settings section, the Checked by value of the rubric problems, and the one-time migration of `progress.db`.

### Surfaces

| Surface | Class |
|---------|-------|
| `cstudy ai` commands, flags and human output; the `[ai]` keys; the `ai status` and `ai usage` documents; the web API's AI endpoints and jobs; instructions, routing rules and limits | Preview: may change in a minor release |
| The AI review record: `ai_reviews` rows, their export rows, and the record's fields in the `ai review` documents | Public: additive only; a new record format is a new `format` value |
| `ai_calls` and `ai_consents` | Not an API, and not in the export: they are this machine's state, free to change in a minor release; an import starts without them |

### Storage

One migration, `0008_ai.sql`, adds `ai_reviews`, `ai_calls` and `ai_consents`, with `IF NOT EXISTS`. `cstudy reset` empties them with the rest. `cstudy export` writes `ai_reviews` and leaves the two others out, and `cstudy import` neither reads nor checks them. The chat milestone adds its transcripts to what an export leaves out unless asked.

## Consequences

- `cstudy` gets its first feature that uses the network at run time. PRD section 3, the non-goal on AI grading, NFR-6 and NFR-12's "no request leaves the machine" change in wording when it ships.
- Users of Anthropic, OpenAI and Google see tokens, and `cost unknown`.
- Two consents per model when you use both the check and AI review; a second workspace asks again and has its own cap.
- An AI review in the page waits for a running job, and blocks a `doctor --fix` while it runs.
- Four request shapes to maintain, pinned by recorded responses; a provider's API change can break the preview until a release.
- `checked_by` of the 16 rubric problems becomes `["rubric", "ai-review"]` for everyone; `--checked-by rubric` keeps the same rows.
- Every fast test runs under the network guard, and a test that needs the network must say so; the guard also serves the offline criteria O1 to O3, which the roadmap now places in v1.1.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| You want a cost for every provider | Prices per model that you set |
| You want reviews with no key or no internet | A local model: the Chat Completions adapter with a base URL and no key |
| Reviews prove inconsistent | ADR 0021 R8's labeled answer sets checked with a real key, tighter instructions, or dropping the feature |
| A provider retires the API its adapter speaks | That adapter's next request shape |
| The `lld` design rubrics want a second opinion | AI review of a design rubric beside the tests, which judges design, never correctness |

## Alternatives considered

| Alternative | Trade-off |
|-------------|-----------|
| A local endpoint as the fourth provider | Nothing leaves the machine and no key is needed, but it is outside the owner's list and the roadmap places it after 1.1; the Chat Completions adapter keeps it a small step |
| Provider SDKs or httpx | Above: dependencies and their review for an opt-in preview |
| Calling providers from the server process | A review takes seconds to minutes: on the worker it would stall every other request, and on a thread of its own it would break the rule that use cases never run at once inside the server |
| Consents and usage in a store per user | One cap and one consent across workspaces, for a new file with its own migrations, backups and reset rule |
| A shipped price table, or prices you set | Estimates for every provider, but stale prices give wrong costs; prices you set stay a later option |
| Forced tool use for Anthropic's structured output | Worked on older models; the Messages API's structured output is generally available, and the domain checks every reply anyway |
| Sending `reference.md` to the reviewer | Sharper on details, but the review would favor the reference's design over another valid one; the rubric already lists what a strong answer covers |
| Exporting the usage log and consents | A simpler "every table" rule, but preview tables would join the export's promise that every 1.x imports every earlier export |
| Letting an AI review count as a pass or change the grade | Against the owner's rule: the grade of a rubric problem stays your own |
