# ADR 0021: A future class of problems is reviewed by a live LLM, with your own key, as an opt-in

| Field | Value |
|-------|-------|
| Status | Accepted as a plan for the future. Nothing here is built, and no phase is committed. The items under [Open to confirm](#open-to-confirm) are confirmed when work starts |
| Date | 2026-11-05 |
| Spec | None yet. Today's behavior stays in [content](../specs/content.md#non-autograded-item-format) and [web-ui](../specs/web-ui.md#settings-view), which carry forward pointers |
| Amends | [PRD](../prd.md): NFR-6, renamed from "Offline" now; once built, the non-goal "no AI grading", section 3 and NFR-12's wording. [ADR 0019](0019-service-projects.md)'s O1 follows this |
| Builds on | [ADR 0015](0015-local-web-ui.md), [ADR 0018](0018-editor-code-intelligence.md) (the budget of an optional chunk), [ADR 0019](0019-service-projects.md) (the requirements list, the environment allowlist), [ADR 0020](0020-catalog-labels.md) (what stays out of graded problems) |

## Context

Some skills cannot be graded deterministically: a written answer, how you answer questions about your experience, a system you draw. Today those are [self-review only](../specs/cli.md#cstudy-solution): the 10 `system-design` and 6 `code-review` items have a `rubric.md`, `cstudy solution` shows it with the reference, and comparing your notes is the review ([content](../specs/content.md#tracks)).

## Decision

### Decided by the owner

| # | Decision (2026-11-05) |
|---|-----------------------|
| O1 | A future class of problems is reviewed by a live LLM, because it cannot be graded deterministically: written answers where you write no code; simulated interviews testing experience and the ability to answer questions; system design on a whiteboard where you draw a system |
| O2 | You provide your own key for OpenAI, Anthropic, Google or OpenRouter, any or all of them |
| O3 | It is a special use case that not everyone will use. The rest of the app needs no internet |
| O4 | Drop "works offline" as a product statement and focus on "works on your own machine". [NFR-6](../prd.md#non-functional-requirements) says this now |

### Names

| Name | What the repository already means by it | Decision |
|------|------------------------------------------|----------|
| "mock interview" | [`cstudy mock`](../specs/cli.md#cstudy-mock): a timed practice session with no reviewer | This feature is a **simulated interview** |
| "review" | A due review in spaced repetition (`cstudy next --review`), and the `code-review` track | The result is an **AI review**, always labelled so. A verb, if one is added, is `cstudy ai-review`, never a bare `review` |

### Open to confirm

Recommended by the assistant and not contradicted by the owner.

| # | Area | Recommendation |
|---|------|----------------|
| R1 | Opt-in | On in Settings, off by default. A problem declares that it needs a review provider, and that appears in the [requirements list](../specs/service-projects.md#what-a-problem-depends-on) planned by ADR 0019. With no key you still see the rubric and self-review, and nothing breaks |
| R2 | Keys | Read from environment variables, or stored in the OS keychain. Never in the workspace, `.cs/`, logs, transcripts or archives; never passed to runners, language servers or containers. The web API accepts a key but never returns one, only whether one is set |
| R3 | Who calls | The local server process, never the page, so the page's CSP does not change. **There is no cstudy server between you and the provider** |
| R4 | Consent and cost | Nothing is sent automatically. Before the first send, cstudy shows the provider, the model and exactly what will be sent. It shows an estimated cost if knowable, and actual usage afterwards, with a token cap. You pick the model; cstudy hardcodes no model ids |
| R5 | Verdict | A problem ships a rubric with items. A review returns schema-validated structured output per item: score, evidence quoted from your answer, and gaps. The stored result records provider, model, rubric version and time |
| R6 | Honesty | Always labelled "AI review", and kept separate from deterministic pass and fail in progress and streaks. **The same answer can get a different review.** You can re-run it and dismiss it |
| R7 | Injection | Your answer is data, never instructions, and the reviewer has no tools. Prompt injection only cheats yourself, so it is **not treated as a security boundary** |
| R8 | Quality | Each rubric ships a small labelled set of good, weak and poor answers, checked by a manual verify step with a real key, never in CI. Tests use a fake provider through a port, following the hexagonal layers, with a provider adapter per API. Structured output and image support differ by provider, so a problem that needs images requires a vision-capable model and says so |
| R9 | Simulated interview | Turn-based, with follow-up questions, a rubric per competency, a transcript stored locally and an optional timer. Generic roles only, never imitating a real company or person. Voice is out of scope |
| R10 | Whiteboard | A canvas in the page, on a lazily loaded chunk, sending both the structured scene and a PNG, along with your written notes ([below](#whiteboard)) |
| R11 | First consumers | The existing 10 system-design and 6 code-review items gain optional AI review, with no change for those who do not use it |

### Keys in practice

| Item | Finding |
|------|---------|
| macOS | The Keychain, through the Python [`keyring`](https://pypi.org/project/keyring/) library (read 2026-11-05) or `/usr/bin/security`, which is present here. To verify at implementation: `security add-generic-password -w` takes the secret as an argument, visible to other processes, so the library looks safer |
| Linux | `keyring` uses the Freedesktop Secret Service or KWallet. A desktop session has one. A headless machine needs a D-Bus session and an unlocked keyring daemon, which is not practical, so **environment variables are the fallback there** |
| New dependency | `keyring` would be a new requirement of `cstudy`, for an opt-in feature. Worth an optional extra, decided at implementation |
| Environment variables | Must not reach user code. Today they would: `_environment` in `adapters/subprocess_runner.py` passes on `os.environ`. So **ADR 0019's allowlist, its P2, is a hard prerequisite for this ADR** |

### Whiteboard

A spike item, not a decision.

| Item | Constraint |
|------|------------|
| Budgets | NFR-12 and [web-ui](../specs/web-ui.md#front-end-assets): the whole bundle at most 1 MB raw and 350 KB gzip without the Vim and code-intelligence chunks; at most 600 KB raw loaded before a file is editable; the code-intelligence chunk at most 64 KB raw and 24 KB gzip. A canvas must load lazily, outside the editor's budget, on a budget of its own, which amends NFR-12 |
| Candidate | An MIT-licensed canvas library such as Excalidraw. Its `LICENSE` reads MIT (read 2026-11-05). Its size is unverified, and it may well exceed every budget above, so the spike measures it against a smaller library or a small canvas of our own |
| The page's CSP | `default-src 'self'`, `style-src` with a nonce, no `unsafe-inline` or `unsafe-eval` (NFR-10). The library must run under that with fonts and assets vendored, and fetch nothing from a CDN. Unverified |
| What is sent | The structured scene, elements and connections as JSON, which is more reliable to reason over; a PNG, for free-form drawing; and your written notes |
| Parity | [FR-16](../prd.md#functional-requirements) says the page never gets behaviour the CLI lacks. Drawing is page-only by nature, so this needs a stated exception. The CLI can still send a scene and image from files |

### Where it plugs in

Hexagonal, as the rest of cstudy is: a `ReviewProvider` port in the application layer, an adapter per API under `adapters/`, a fake in tests, and no provider SDK unless one proves necessary. An OpenAI-compatible adapter can serve OpenRouter too, which a spike confirms.

## Order

No phase commitments beyond an order, and it sits after ADRs 0019 and 0020 unless the owner reorders it.

| Step | Scope |
|------|-------|
| 1 | Provider port and keys, including ADR 0019's P2 if it has not shipped |
| 2 | Written answers on existing items |
| 3 | Simulated interview |
| 4 | Whiteboard, after its spike |

## Consequences

- Once built, cstudy has one optional feature that uses the internet. Everything else keeps needing it only for installs. NFR-6 says so.
- The PRD's non-goal "No AI grading of code, designs or behavioral answers" and section 3, "The product contains no AI features", stay true until step 1, and both change then. Each carries a pointer now. Code is still never graded by an LLM, and `cstudy verify`, comparators and `cstudy submit` stay deterministic.
- NFR-12's "No request leaves the machine" holds for the page, since the server process makes the call, and its wording becomes "no request from the page" at step 1.
- [`cstudy done`](../specs/cli.md#cstudy-done), the schedule and the streak are unaffected: an AI review neither finishes an attempt nor changes a grade. Where a review lives, a new table in `progress.db`, and whether `cstudy export` includes transcripts, which you may commit, are decided at step 2.
- Your answers go to the provider you chose, under that provider's terms. The consent screen says which.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| Users want reviews without a key or with no internet | A local model, behind the same port |
| Reviews prove too inconsistent to help, on the labelled sets | Tighter rubrics, or dropping the feature |
| The canvas cannot fit any sensible budget | Whiteboard as an imported file, or no whiteboard |

## Alternatives considered

| Alternative | Trade-off |
|-------------|-----------|
| Self-review only, as today | No keys, no cost and no variation, and it stays the default for anyone who does not opt in. It gives no second opinion and cannot ask a follow-up question |
| A local model | No key and no data leaving your machine, but heavy for an 18 GB machine, and weaker. It can be added later behind the same port. OpenAI-compatible local endpoints are a possible later adapter |
| Shipping cstudy's own reviewer service | Rejected by O2 and by the product's shape: there is no cstudy server |
| Reviewing code with an LLM too | Code has a deterministic verdict, and a second judge is what ADR 0010 and ADR 0014 rejected |
