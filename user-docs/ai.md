---
title: "The AI preview: keys, consent and AI review"
summary: Turn on the optional AI preview with your own provider key, see and agree to what is sent, stay within a daily token cap, and get an AI review of your system design and code review notes.
section: Settings and help
order: 122
---

# The AI preview: keys, consent and AI review

The AI preview adds optional features that send a request to an AI model, with your own key for the provider you choose. It has two today:

- **AI review**: a second opinion on your notes for a system design or code review problem, criterion by criterion against its rubric. It never changes a grade.
- **The check**: one small test request to each model you set up, so you see your keys and models working before a review needs them.

The preview is off by default, and with it off nothing leaves your machine. With it on, nothing is sent until you run a command that sends, or press an AI button in the web UI, and agree to send to that model. Requests go straight from your machine to the provider, under your account's terms: there is no cstudy server in between.

It is a preview: its commands, settings and output may change in a minor release. The AI reviews it stores are kept across upgrades, and `cstudy export` includes them.

## Quick path

1. Turn it on: run `cstudy config edit` and set `enabled = true` under `[ai]`, or tick **Turn on AI (preview)** in the AI section of Settings ([turn it on](#turn-it-on)).
2. Save your key. It asks for the key with a hidden prompt:

   ```bash
   cstudy ai key anthropic
   ```

3. Choose a model from the ids your key can use, and set it as `ai.model` with `cstudy config edit` or in Settings:

   ```bash
   cstudy ai models anthropic
   ```

4. Check it. The first time, it shows what it sends and asks you to agree:

   ```bash
   cstudy ai check
   ```

5. Start a system design or code review problem, write your answer in its notes file, then ask for a review:

   ```bash
   cstudy start url-shortener
   cstudy ai review url-shortener
   ```

The AI section of Settings in the web UI does steps 1 to 4 too.

## Turn it on

The preview has six keys, in the `[ai]` table of your [`config.toml`](settings.md#your-configuration):

```toml
[ai]
enabled = true
routing = "fixed"                # or "auto"
model = "anthropic:<model id>"   # one of the ids cstudy ai models lists
daily_token_cap = 500000
```

| Key | Default | Does |
|-----|---------|------|
| `ai.enabled` | `false` | Turns the preview on. Off, nothing leaves this machine |
| `ai.routing` | `"fixed"` | `fixed`: every task uses `ai.model`. `auto`: each task uses its tier, `ai.fast` or `ai.strong` ([routing](#routing)) |
| `ai.model` | not set | The model of fixed routing, such as `"anthropic:<model id>"` |
| `ai.fast` | not set | Auto routing's fast tier |
| `ai.strong` | not set | Auto routing's strong tier. AI review uses it |
| `ai.daily_token_cap` | `500000` | Input and output tokens per day, every AI task together, in this workspace ([the cap](#the-daily-token-cap)) |

A change applies at the next command. A web UI page that is open reads `ai.enabled` again after a reload.

With the preview on, no other command changes: only the `cstudy ai` commands, the `ai` row of `cstudy doctor` and the web UI's AI section and actions read your keys, and only the commands and actions that send reach a provider.

## Your keys

Keys live in `credentials.toml`, a file of keys only, and nowhere else. `cstudy` never reads a key from an environment variable.

### Where the file is

`credentials.toml` sits beside your `config.toml`: `~/.config/coding-study/credentials.toml`, or under `$XDG_CONFIG_HOME/coding-study/` when that variable is set, or beside the file `CSTUDY_CONFIG` names. `cstudy config path` prints where `config.toml` is, and the `keys` line of `cstudy ai status` names the keys file.

### Save and remove a key

```bash
cstudy ai key anthropic            # asks for the key; what you type is hidden
cstudy ai key anthropic --remove   # deletes that key
```

`cstudy ai key` never takes the key as an argument, so it stays out of your shell history, and it never prints it. In a script, it reads one line of standard input. It does not try the key: `cstudy ai check` does. It works with AI off and needs no workspace. A key is one line of text with no spaces; anything else is refused, exit 3.

In the web UI, the **Keys** group of Settings' AI section has a field per provider. A key you type is saved when you choose **Save**, and never shown again: the row then says `key set`. **Remove** deletes it at the next Save.

The file looks like this, one table per provider with a key:

```toml
[anthropic]
api_key = "<key>"

[openrouter]
api_key = "<key>"
```

`cstudy` writes it with mode `0600`, readable by you alone, and makes its folder with mode `0700` when it is missing. It rewrites the whole file whenever a key changes, so a comment you add by hand does not survive, and it deletes the file with its last key. You may also write the file yourself: `cstudy` reads it whatever its mode. A table other than the four providers, a key other than `api_key`, or an empty value makes the file fail to load: the `cstudy ai` commands that need a key then exit 4 and name the problem, `cstudy ai status` and `cstudy doctor` show it, and nothing else fails.

### Keep keys out of repositories

Never put a key in your workspace or in a repository. `cstudy` refuses to read or write `credentials.toml` when it would lie inside a workspace, as a `CSTUDY_CONFIG` there would put it, and exits 3:

```text
error: credentials.toml would be inside this workspace (<path>): keys never go in a workspace; point CSTUDY_CONFIG at a config.toml outside it
```

If you keep `config.toml` in a dotfiles repository, keep `credentials.toml` out of it: add a line to that repository's `.gitignore`.

```text
credentials.toml
```

`cstudy doctor` warns while `credentials.toml` lies inside a Git working tree, and its fix names the `.gitignore` to add it to ([check your setup](doctor.md#row-reference)).

A key travels only in the request header to its own provider. It is never in your workspace, `progress.db`, an export, `--json` output, the web UI's answers, a log or an error message: when a provider's message repeats your key, `cstudy` shows `<key>` in its place. Runners, language servers and the containers of service projects never get it. Your own code, when a problem runs it on your machine, runs as you and could read any file you can, this one included; a service project's container sees only its project folder.

## Providers and models

`cstudy` speaks to four providers, each with your own key: `anthropic`, `google`, `openai` and `openrouter`. A model is the provider, a colon, and the id the provider gives the model: `anthropic:<model id>`. An id may hold more colons and slashes, as in `openrouter:<vendor>/<model>:<variant>`.

`cstudy` names no model of its own. List the ids your key can use:

```bash
cstudy ai models openrouter
```

It prints the ids one per line, sorted. It needs AI on and that provider's key, and sends only the request for the list: no consent, no tokens counted, and no usage row. In Settings, **Load models** beside a provider with a key does the same, and offers the ids as suggestions in the model fields.

`config.toml` refuses a model it cannot read, by its key, as it refuses any wrong value: `ai.fast: unknown provider "gemini"; use one of anthropic, google, openai, openrouter`. Whether the provider has that model shows at the first request, or with `cstudy ai check`.

Requests use your system's certificates and the proxy settings `HTTPS_PROXY` and `NO_PROXY`. A request that fails is not retried: run the command again.

## Routing

`ai.routing` says which model each task uses.

| Task | `fixed` | `auto` | Output limit | Waits at most |
|------|---------|--------|--------------|---------------|
| AI review | `ai.model` | `ai.strong` | 16,000 tokens | 300 s |
| The check | `ai.model` | `ai.fast`, then `ai.strong`; once when both name the same model | 1,000 tokens | 60 s per model |

`fixed` is the default and the simplest start: one model for everything. `auto` lets a cheaper, quicker model serve the light tasks and a stronger one the reviews:

```toml
[ai]
enabled = true
routing = "auto"
fast = "openrouter:<model id>"
strong = "anthropic:<model id>"
```

A task never falls back to another model. When the model it needs is not set, or its provider has no key, it is refused before anything is sent, exit 3, with what to set:

```text
error: ai.model is not set: choose the model of fixed routing in Settings or with cstudy config edit
error: ai.strong is not set: auto routing serves AI review from the strong tier
error: no key for anthropic, which ai.model uses: cstudy ai key anthropic, or Settings
```

## Consent

Nothing is sent to a model for a purpose before you agree to send to it. A purpose is `review`, for AI review, or `check`, for the check. The first time a request would go to a model for a purpose, `cstudy` shows what it sends and asks:

```text
AI review of url-shortener sends, from this machine to anthropic, model <model id>:
  instructions review-1         2.1 KB
  prompt.md                     1.6 KB
  rubric.md, 28 criteria        3.2 KB
  your notes                    4.2 KB  notes/system-design/url-shortener.md
about 2,800 tokens in and up to 16,000 out · today 12,400 of 500,000 tokens
Your anthropic account's terms apply to what it receives. cstudy asks once for this model and AI review.
Send it? [y/N]
```

`y` records your consent and sends. `n`, or Enter alone, prints `not sent` and exits 0. Once you agree, `cstudy` does not ask again for that model and purpose. Using one model for both the check and AI review asks twice, once per purpose.

| Where | How you agree |
|-------|---------------|
| A terminal | The question above |
| A script, with no terminal | It exits 3 and sends nothing: `AI review needs your consent to send to anthropic:<model id>: run it once at a terminal, or cstudy ai consent anthropic:<model id> --purpose review` |
| Ahead of time | `cstudy ai consent anthropic:<model id> --purpose review` records it without a question |
| The web UI | A dialog titled `Send to anthropic:<model id>?` lists the same items. **Send** records your consent and starts; **Cancel**, which has the focus, sends nothing |

No `--yes`, setting or environment variable agrees for you. Your consents belong to the workspace: they are kept in its `progress.db`, beside the work whose content is sent, so another workspace asks again.

Take a consent back with `cstudy ai consent anthropic:<model id> --purpose review --revoke`, or **Revoke** in the **This workspace** group of Settings' AI section, which acts at once. `cstudy reset` removes every consent. The next request then asks again.

## What is sent

| Task | Sent | Never sent |
|------|------|------------|
| AI review | Fixed instructions; the problem's title and prompt; for a code review, the change you review; the rubric's criteria, numbered `C1`, `C2` and on; and your notes file as it is on disk | The reference answer, the notes template, any other file, other attempts, your progress, your settings, your paths and your name |
| The check | Fixed instructions and the message `Reply with {"ok": true}.` | Anything of yours |
| Listing models | The request for the list | Anything of yours |

See exactly what a review would send, without sending it, and without a key or a consent:

```bash
cstudy ai review url-shortener --dry-run
```

It prints the instructions and the message between `=== instructions review-1 ===`, `=== message ===` and `=== not sent ===` lines, then the model it would use and the estimated tokens.

Your key goes only in its request header. Each request names `cstudy` and its version, and nothing else about you or your machine.

## The daily token cap

`ai.daily_token_cap` limits the tokens of every AI task together, input and output, per day of your machine's clock, in this workspace. It is 500,000 by default, and it always applies: set it as high as you like.

Before a request leaves, `cstudy` adds its estimate to the tokens counted today. The estimate is the request's text in bytes divided by 4, plus its output limit. When the sum would pass the cap, the request is refused, exit 3, and nothing is sent:

```text
error: the daily token cap is reached: 498,120 of 500,000 tokens today, and this review needs up to 18,800; raise ai.daily_token_cap or wait until tomorrow
```

Each request counts the tokens its provider reported. A request that got no usage report, after a timeout, a dropped connection or `Ctrl+C`, counts its estimate. Listing models counts nothing.

## Usage and cost

```bash
cstudy ai status          # today, the settings, the keys and the consents
cstudy ai usage           # the last 7 days, by day, provider, model and purpose
cstudy ai usage --days 30
```

```text
$ cstudy ai status
ai        on · routing auto · fast openrouter:<model id> · strong anthropic:<model id>
review    ready · strong anthropic:<model id>
check     ready · fast openrouter:<model id>, strong anthropic:<model id>
keys      anthropic, openrouter · in ~/.config/coding-study/credentials.toml
consents  anthropic:<model id> review (2026-11-16) · openrouter:<model id> check (2026-11-16)
today     12,400 of 500,000 tokens · 3 requests · $0.00003 known, 2 requests without a reported cost
```

```text
$ cstudy ai usage --days 2
DAY         PROVIDER    MODEL       PURPOSE  REQUESTS  INPUT  OUTPUT  COST
2026-11-15  anthropic   <model id>  review          2  9,812   4,820  -
2026-11-16  openrouter  <model id>  check           1     40      12  $0.00003
total       3 requests, 0 failed · 14,684 tokens counted · $0.00003 known, 2 requests without a reported cost
```

Both work with AI off, and both take `--json`. A line of `cstudy ai status` says why a task cannot run, such as `ai.strong is not set` or `no key for openrouter`.

The cost shown is only what a provider reports with its answer. Today `openrouter` reports each request's cost in US dollars; the others report tokens only, shown as `cost unknown`, or `-` in a table. `cstudy` holds no price list, so tokens are always the measure to watch.

Usage also shows in Settings (today and the last 7 days), on each review, and in the consent question.

## Check your models

```text
$ cstudy ai check
fast    openrouter:<model id>   ok · 1.4 s · 52 tokens · $0.00003
strong  anthropic:<model id>    FAIL anthropic refused the key (401): set it again with cstudy ai key anthropic
```

`cstudy ai check` sends a fixed message to each model the routing names and asks for `{"ok": true}` in a fixed format, so the key, the model id and structured answers are each seen working. Each line shows the tier (none under fixed routing), the model, and `ok` with the time, the tokens and the known cost, `FAIL` with the reason, or `not sent` when you answered no to its question. A failing model does not stop the check of the next. It exits 0 when every model passed or was not sent, 4 when one failed, and 3 when it is refused before sending. **Check** in Settings runs it too.

## AI review

AI review reads your notes on a system design or code review problem against the problem's rubric, and returns a verdict for each criterion, with quotes from your notes and what is missing. It is always labeled AI review, and it is a second opinion, not a grade: your grade stays your own rating.

These problems show `rubric + AI review` in the Checked by column of the web UI, whatever your settings, and `cstudy list --checked-by ai-review` lists them.

### Run a review

```bash
cstudy ai review url-shortener   # the problem's attempt in progress, else its latest
cstudy ai review                 # the problem of your active attempt
```

It reviews the problem's attempt in progress, or its latest attempt when none is open, and reads that attempt's notes file, `notes/<track>/<slug>.md`, as it is on disk now. You may review before you rate the attempt: revealing the rubric never lowers a rubric problem's grade. After the consent question the first time, it prints `reviewing with anthropic:<model id>, up to 300 s` and waits for the answer. `Ctrl+C` stops it, exit 130.

It is refused, exit 3, with nothing sent, when:

| Case | Message |
|------|---------|
| The problem is not a rubric problem | `two-sum is checked by tests; AI review is for rubric problems (system-design and code-review)` |
| It has no attempt | `no attempt of url-shortener yet: start it with cstudy start url-shortener` |
| The notes file is missing | `notes/system-design/url-shortener.md is missing: AI review reads your notes` |
| The notes are still the template | `your notes are still the template: write your answer in notes/system-design/url-shortener.md first` |
| The notes are too large | `your notes are 80 KiB; AI review reads at most 64 KiB` |
| A mock interview runs | `cstudy ai review is locked during the mock interview (group-anagrams, lru-cache; 31:20 left); it unlocks when the timer ends or every problem is done` |

AI off, an unset model, a missing key, the daily cap and a missing consent refuse it the same way ([routing](#routing), [consent](#consent)).

### Read a review

```text
AI review · url-shortener · attempt 12 · anthropic:<model id> · review-1
The same answer can get a different review. It changes no grade and no schedule.

Requirements and scope
  met      Separates the create path from the redirect path and treats redirect …
           "redirects stay fast even when creating links is down"
  partly   States that codes are never reused and destinations never change …
           gap: codes are unique, but nothing says destinations never change
  missed   Asks about or states analytics freshness and loss tolerance …
           gap: nothing on how fresh click counts must be
…
summary  Strong on the API and the data model; the estimates stop at averages, …
result   18 met · 6 partly · 4 missed of 28 · 9,812 tokens in, 2,410 out · cost unknown
```

| Part | Says |
|------|------|
| Verdict | `met` when your notes cover the criterion, `partly` when they cover part of it, `missed` when they do not |
| Quotes | Up to three short quotes from your notes that support the verdict. A quote the model gives that is not in your notes is left out |
| `gap` | What your notes lack for that criterion |
| `summary` | Strengths first, then the most important gaps |
| `result` | The counts, the tokens and the known cost |

The instructions tell the model to treat your notes as an answer to review, never as instructions to follow. Its text is shown as plain text. The same notes can get a different review on another run, so read it as one opinion beside the rubric and the reference answer that `cstudy solution` shows you.

A reply that misses a criterion, or does not follow the review format, stores nothing and exits 4; its tokens still count. `--json` prints the review as one JSON document.

### What a review never does

A review never finishes an attempt, and never changes a rating, a grade, the review schedule, a status, mastery, the weakness score or `cstudy stats`. It never counts as a pass, and it records no help on the attempt. It is stored beside the attempt it reviewed, with the provider, the model and the rubric it was made against.

### Earlier reviews

```bash
cstudy ai review url-shortener --list   # every review of the problem, newest first
cstudy ai review --show 3               # one review in full
cstudy ai review --dismiss 3            # mark it dismissed; it stays stored
```

Run `cstudy ai review` again for a new review: each one is kept. A review you dismiss stays stored and listed, marked `dismissed`, and the web UI no longer shows it as the attempt's latest. A review whose notes changed since says `notes changed since this review` under its header. `--list`, `--show` and `--dismiss` send nothing: they work with AI off and during a mock interview.

### In the web UI

With AI on, the Attempt view of a system design or code review problem has an **AI review** button in its header, and the review panel in the results' place. Before any review, the panel says what AI review does and sends. Save your notes first: AI review reads them from disk. The first time for a model, the consent dialog asks; then the panel says `reviewing with anthropic:<model id>…` with a **Cancel** button, and shows the review when it is ready, with **Review again**, **Dismiss** and the attempt's earlier reviews. An AI review runs as a job of the page, so it waits while another job, such as **Fix** in the Health view, runs.

The Problem view's history shows the latest review of each attempt (`AI review: 18 met · 6 partly · 4 missed of 28`) with **View**, which opens the attempt's reviews, whatever your AI settings. A review you make in the terminal shows in an open page too.

## With AI off

With `ai.enabled` false, the default:

- No request goes to any provider. `cstudy ai check`, `cstudy ai models` and a `cstudy ai review` that would send exit 3: `AI is off: turn it on with ai.enabled = true (cstudy config edit) or in Settings`. The web UI's AI actions are refused the same way.
- Only the `cstudy ai` commands, the `ai` row of `cstudy doctor` and the AI section of Settings read `credentials.toml`.
- The web UI shows the AI section in Settings, where you set the preview up, and the reviews you already have in a problem's history; no other AI control.

`cstudy ai status`, `cstudy ai usage`, `cstudy ai key`, `cstudy ai consent` and `cstudy ai review` with `--dry-run`, `--list`, `--show` or `--dismiss` work with AI off, since they send nothing. Everything else works as it does without the preview, except two things you may notice: the Checked by value of the system design and code review problems, and the one-time migration of `progress.db` that adds the AI tables ([upgrading](upgrading.md#the-ai-preview)).

## When a request fails

A provider's failure exits 4. The request is still recorded, as failed, with the tokens the provider reported, and nothing is retried: fix the cause, then run the command again. No message holds your key.

| You see | Do |
|---------|----|
| `anthropic refused the key (401): set it again with cstudy ai key anthropic` | The key is wrong, revoked or lacks access: save a new one |
| `openai is limiting this key's requests (429): try again later` | Wait, or check your account's limits with the provider |
| `google has no model <model id>, or it cannot answer in a JSON schema: see cstudy ai models google` | Choose an id that `cstudy ai models` lists, and one that answers in a JSON schema |
| `anthropic declined to answer this request` | The provider refused the content. Nothing was stored |
| `the reply stopped at its 16,000-token limit before it was complete` | The answer ran past its output limit. Run it again, or try another model |
| `could not reach api.anthropic.com: <reason>` | Check your network, proxy (`HTTPS_PROXY`) and certificates |
| `anthropic did not answer within 300 s` | The provider was slow. Run it again later |
| `openrouter failed (502): <message>` | The provider had a problem. Run it again later |
| `the model's reply did not follow the review format: <reason>; nothing was stored` | The model's answer did not fit. Run it again, or choose a stronger model |

[Troubleshooting](troubleshooting.md#the-ai-preview) lists the messages of a refusal, which exit 3 and send nothing.
