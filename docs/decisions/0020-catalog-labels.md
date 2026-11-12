# ADR 0020: The catalog gains three independent labels: domain, role and scope

| Field | Value |
|-------|-------|
| Status | Phases 1 and 2 implemented. Phase 3 is planned, and nothing of it is built. The owner took R1 to R7 under [Open to confirm](#open-to-confirm) as recommended on 2026-11-06. The [2026-11-11 amendment](#amendment-2026-11-11-data-infrastructure-systems-software-design-and-frontend) adds five domains, two roles and three patterns |
| Date | 2026-11-05, amended 2026-11-11 |
| Spec | [content](../specs/content.md#labels), [catalog](../specs/catalog.md), [problem-format](../specs/problem-format.md#metayaml), [authoring](../specs/authoring.md#static) (S24), [cli](../specs/cli.md#cstudy-list) and [web-ui](../specs/web-ui.md#problems-view) describe phase 1. [catalog](../specs/catalog.md#practical-85-problems) lists the first wave, and [S13](../specs/authoring.md#static) holds the language rule of phase 2 |
| Amends | [PRD](../prd.md) (FR-3, its description and persona), [ADR 0012](0012-go-and-rust.md) (every language on every problem, by the [language rule](#rule-changes)) |
| Builds on | [ADR 0001](0001-data-driven-tests.md), [ADR 0004](0004-original-problem-wording.md), [ADR 0014](0014-project-problems.md), [ADR 0019](0019-service-projects.md). Reviewed items are [ADR 0021](0021-ai-reviewed-problems.md) |

## Context

The owner wants cstudy to grow into a study tool for engineers with lots of problem projects, categorized by domain and role, at a range of complexity levels. The first new catalogs are security problems for security engineers and AI/LLM problems. Nothing in the catalog can say that today.

| Field | What it says | Where it is closed |
|-------|--------------|--------------------|
| `track` | The type of practice | Enums in `schemas/meta.schema.json` (`dsa`, `practical`, `lld`, `concurrency`, `debugging`) and `schemas/item.schema.json` (`system-design`, `code-review`) |
| `kind` | The shape of a problem | An enum in `schemas/meta.schema.json` only (`function`, `design`, `progressive`, `concurrent`, `project`). An item has no `kind`: `cstudy list --kind item` and the `kind: item` of `--json` are made up by the list ([cli](../specs/cli.md#cstudy-list)) |
| `patterns` | The DSA technique | `PATTERNS` in `domain/taxonomy.py`, and again in `$defs/pattern` of `schemas/meta.schema.json`, as the module's docstring says. Items have no `patterns` |
| `difficulty` | How hard | Enums in both schemas |

Neither schema has a tags, roles or domain field, and both set `additionalProperties: false`, so each new field needs a schema change. `batch` and `stream` are columns of [catalog](../specs/catalog.md#dsa-catalog)'s DSA tables, not fields. The catalog has 270 entries, 254 problems and 16 non-autograded items ([catalog](../specs/catalog.md)), which `problems/` and `tracks/` confirm.

## Decision

### Decided by the owner

| # | Decision (2026-11-05) |
|---|-----------------------|
| O1 | cstudy grows into a study tool for engineers with lots of problem projects, categorized by domain and role, ranging in levels of complexity |
| O2 | The first new catalogs are security problems for security engineers and AI/LLM problems |
| O3 | Plan only. Nothing is built |

### Approved in outline

Three independent labels, added to problems and items. `track`, `kind`, `patterns` and `difficulty` stay.

| Label | Field | How many | Answers |
|-------|-------|----------|---------|
| domain | `domains` | One or more | What subject is it about? |
| role | `job_roles` | One or more | Who is it for? |
| scope | `scope` | Exactly one | How big is the thing you work on? |

- **No `security` track.** A track says what type of practice this is, not the subject. A security problem is `practical` or `debugging` with `domains: [security]`.
- **`difficulty` stays.** Scope and difficulty are independent: a project can be easy and a function hard.

### Names

| Name | Collision found | Decision |
|------|-----------------|----------|
| `roles` | `approaches[].role` (`brute`, `intermediate`, `optimal`) in `$defs/approach` of `schemas/meta.schema.json`, in the `approaches` entries of `schemas/web-api.schema.json`, in about a dozen lines of `domain/`, and throughout [problem-format](../specs/problem-format.md#approaches-and-complexity). A top-level `roles` would pass validation, since the nesting differs, but `roles: [backend]` above `role: optimal` in one `meta.yaml` reads like a relation, and a search for `role` finds both | The field is **`job_roles`**. The filter is `--role` and the column is "Role", because no flag or column uses that word today. The alternative `roles` is shorter, at the cost above |
| `domain` | `domain/` is the hexagonal layer ([architecture](../architecture.md)), a prose collision only. No field uses it | The field is `domains`, plural like `patterns` and `languages`, and the filter is `--domain`, as `--pattern` filters `patterns` |
| `scope` | [catalog](../specs/catalog.md)'s non-DSA tables already have a prose column called `scope`, holding what each row covers. A stress invariant has a `scope` in `schemas/tests.schema.json`, and `NextScope` in `domain/next_selection.py` and the [selection](../specs/progress-and-scheduling.md) use the word for what `cstudy next` considers. No flag uses it: `cstudy list` and `cstudy next` have no `--scope` | Keep `scope` as approved. The catalog's prose column is renamed `covers` in phase 1, since a row cannot hold two columns of that name. The other two are different contexts and stay |
| `scope: function` | `kind: function`. `kind: design` with `scope: function` reads oddly | Defined below as "one function or class". Open to confirm in R4 |

### Vocabulary

Proposed initial lists, which the owner confirms in R1 and R2.

| `domains` value | Meaning |
|-----------------|---------|
| `algorithms` | Data structures and algorithms, language pitfalls |
| `backend` | Services, APIs, data, design of backend components |
| `security` | Authorization, tenancy, validation, defensive engineering |
| `identity` | Tokens, sessions, login flows, provisioning |
| `ai-llm` | The code around models: clients, retrieval, evaluation, cost |
| `fintech` | Money, ledgers, insurance |

| `job_roles` value | Meaning |
|-------------------|---------|
| `general` | Any software engineer. Added to the outline, so that 212 algorithm rows need not list every role |
| `backend` | Backend engineers |
| `platform` | Platform and infrastructure engineers |
| `security-engineer` | Security engineers |
| `ai-engineer` | Engineers who build on models |
| `ml-engineer` | Engineers who train and evaluate models |

| `scope` value | Meaning |
|---------------|---------|
| `function` | One function or class, in one file, with no folder or process of yours: `kind` `function`, `design`, `progressive`, `concurrent`, and code review items |
| `project` | A folder of files: `kind: project`, including every service project |
| `system` | Several services. Today that means the design discussions of the `system-design` items, and a graded, learner-built one is [later design](#the-map-by-size) |

### Vocabulary rules

| Rule | Detail |
|------|--------|
| Closed lists | Free-form tags drift. Each list is extended deliberately, by a change to its spec row and module |
| Where | In the domain layer, as patterns are: `DOMAINS` and `JOB_ROLES` in `domain/taxonomy.py`, and the scope values there too |
| The schemas | `meta.schema.json` and `item.schema.json` list the same values as `$defs`, as they do for patterns. A fast test holds the module and both schemas equal, which patterns do not have |
| Validation | A new static check, S24: a catalog problem or item has all three. `kind: project` means `project` or `system`; another kind means `function`; a `system-design` item means `system`; a `code-review` item means `function`. Item checks live in `domain/item_checks.py` |
| Your own problems | The fields are optional in the schemas and required by S24 on catalog content only, as S13 tells `meta.workspace` apart. A workspace problem without them keeps working, listed as `-`. `cstudy new` writes defaults by template |
| The index | The [index cache](../architecture.md#index-cache) stamps each entry with the schema's mtime and size, so a schema change re-reads everything. No version bump is needed. NFR-2's 500 ms is unaffected, since the index already stores the whole validated document |

### Backfill

One pass over the 270, in one commit: a throwaway script writes the three fields from the mapping below into every `meta.yaml` and `item.yaml`, S24 then requires them, and the script is not kept. `progress.db` keys on the slug, so progress does not move. Fixtures and templates get them where they are catalog-like.

| Source | Rows | `domains` | `job_roles` | `scope` |
|--------|------|-----------|-------------|---------|
| Track `dsa`, every kind | 196 | `algorithms` | `general` | `function` |
| Track `debugging` | 16 | `algorithms` | `general` | `function` |
| Track `practical`, 0186 to 0191 and 0248, `progressive` | 7 | `backend` | `backend` | `function` |
| Track `practical`, 0214 to 0228, insurance | 15 | `fintech` | `backend` | `function` |
| Track `practical`, 0249 to 0254, `project` | 6 | `backend`, `fintech` | `backend` | `project` |
| Track `lld` | 8 | `backend` | `backend` | `function` |
| Track `concurrency` | 6 | `backend` | `backend`, `platform` | `function` |
| Track `system-design` | 10 | `backend` | `backend`, `platform` | `system` |
| Track `code-review` | 6 | `backend` | `backend` | `function` |
| **Total** | **270** | | | |

0214 to 0228 are insurance tasks: [catalog](../specs/catalog.md#practical-85-problems) calls them that, and their titles agree (premium rating, unearned premium, coverage gaps, loss ratio).

Proposed overrides, to confirm in R3:

| Row | Adds | Why |
|-----|------|-----|
| `banking-system`, `scheduled-transfers-bank`, `bank-transfers`, `payments-ledger`, `review-payment-retry` | `fintech` | Money and ledgers, by their [catalog](../specs/catalog.md) rows |
| `review-auth-endpoint` | `security`, `identity`, with `security-engineer` | The row names SQL built by concatenation, non-constant-time comparison and secrets in logs |
| `api-gateway` | `platform` as a role | Routing, limits and circuit breakers |

### Where the labels show

| Surface | Change |
|---------|--------|
| [`cstudy list`](../specs/cli.md#cstudy-list) | `--domain D`, `--role R`, `--scope S`. Like `--pattern`, each is one value and matches any listed value. They combine with the others by AND. The table's columns stay. `--json` entries gain `domains`, `job_roles` and `scope`, an additive change |
| [`cstudy next`](../specs/cli.md#cstudy-next) | The same flags. **A catch:** its default scope is `next.tracks`, default `["dsa"]` ([PRD Q9](../prd.md#8-open-questions)), so `cstudy next --domain security` would find nothing. A label filter with no `--track` therefore searches every track. A new problem outside `dsa` falls in its track's weakness group ([selection](../specs/progress-and-scheduling.md#weakness-score)), so a domain gets no weakness of its own in this plan |
| [Problems view](../specs/web-ui.md#problems-view) | Domain, Role and Scope filters, kept in the route's query as the others are, and a Scope column. `GET /api/v1/problems` returns entries of `cstudy list --json`, so it gains the fields with it |
| [catalog](../specs/catalog.md) | New tables carry `domains`, `job_roles` and `scope` as binding columns. Existing tables get a line per section with that section's values and an exceptions list, not three columns on 270 rows. `scope` the prose column becomes `covers` |
| [problem-format](../specs/problem-format.md#metayaml), [content](../specs/content.md#non-autograded-item-format) | The field tables |
| The website's catalog sync | **No change now.** It lives in another repository and was not read for this ADR. The fields are additive, and no `track` or `kind` value changes, so a reader that ignores unknown fields keeps working. It may want the filters, and a page per domain, when phase 2 ships |

### The first wave

Original, function-size, needing no service projects. Python and TypeScript first. `track: practical` unless noted. Maps and records are not in the type DSL ([Type DSL](../specs/problem-format.md#type-dsl)), so structured input travels as arrays and lists.

| Problem | `kind` | `domains` | `job_roles` | Notes |
|---------|--------|-----------|-------------|-------|
| Token claim validator | `function` | `security`, `identity` | `security-engineer`, `backend` | Decoded claims and an explicit time. The signature is checked by the caller, so no cryptography is needed |
| Refresh-token rotation with reuse detection | `design` | `security`, `identity` | `security-engineer`, `backend` | Opaque token ids; explicit timestamps |
| Authorization policy engine | `function` or `design` | `security` | `security-engineer`, `backend` | Deny overrides, inheritance |
| Calibration metrics | `function` | `ai-llm` | `ml-engineer`, `ai-engineer` | Fixed predictions, `float` comparator |
| Token cost reconciler | `function` | `ai-llm` | `ai-engineer` | Invented prices, `decimal` |
| BM25 hybrid ranker | `function` | `ai-llm` | `ai-engineer`, `ml-engineer` | Fixed documents and scores, a stated tie-break |
| Stream reassembler | `function` or `design` | `ai-llm` | `ai-engineer` | Fragments as strings, out-of-order and truncated |

`track: debugging` with `stub: buggy` already fits function-size "fix the vulnerability" problems, with no rule change, since that track may list any subset of languages.

### Rule changes

| Rule | Today | Change |
|------|-------|--------|
| S13, every language | `_lists_every_language` in `domain/static_checks.py` makes a catalog problem list every language that can express it, unless its track is in `LANGUAGE_SUBSET_TRACKS` (`concurrency`, `debugging`, in `domain/problem.py`), or it is a workspace or project problem. `practical` is not in the set, so the first wave fails S13 as it stands | Recommended: a new `LANGUAGE_SUBSET_DOMAINS` (`security`, `identity`, `ai-llm`), checked beside the track. Adding `practical` to `LANGUAGE_SUBSET_TRACKS` is simpler, but loosens all 28 rows of that track. It also updates FR-3, [catalog](../specs/catalog.md#rules)'s Languages rule and `ALL_LANGUAGES`'s docstring |
| Rust and cryptography | Rust's standard library has no HMAC or SHA, and `std::hash` gives only a non-cryptographic hasher (source: the Rust standard library's documentation, not re-read for this ADR). The vendored crates in `runners/rust/vendor/` hold none either: `arrayvec`, `autocfg`, `chrono`, `num-traits`, `pin-project-lite`, `proc-macro2`, `quote`, `rust_decimal`, `syn`, `tokio`, `tokio-macros`, `unicode-ident`. Builds run with `--offline` ([runners](../specs/runners.md#rust-build-details)) | Recommended: the first wave needs no cryptography, as above, so nothing is vendored. A later problem that does need it lists a language subset under the rule above, or vendors an HMAC crate and its dependencies. The other five languages have these in their standard libraries |
| S14, project track | A project is on track `practical` | Relaxed for service projects by [ADR 0019](0019-service-projects.md#schema-rules-to-relax), so that a `debugging` project is possible |
| Catalog ids | Fixed in [catalog](../specs/catalog.md#id-order), the highest being 0254 | New rows continue at 0255 |

### The map by size

| Scope | Security and identity | AI and LLM | Needs |
|-------|-----------------------|------------|-------|
| `function` | The [first wave](#the-first-wave) | The [first wave](#the-first-wave) | Rule changes above |
| `project` | Fix tenant data leaks; SSRF URL fetcher; OIDC callback repair; row-level security | Resilient completion client; tool-calling loop; cache-stable history | [ADR 0019](0019-service-projects.md), through its mock server extensions and multi-step cases |
| `system` | SCIM deprovisioning across sessions and keys | An assistant whose code gates tool calls | Later design: [ADR 0019](0019-service-projects.md#later-learner-built-systems) plans one app per problem |
| `system`, not graded | | | Non-autograded items, as the 10 `system-design` items already are. They need nothing new |

### Catalog content rules

Recommended, in R5.

| Area | Rule |
|------|------|
| Security | Problems are defensive: you fix logic flaws such as authorization, tenancy and validation. Starters ship no exploit steps, no command-execution bugs and no memory bugs. Grader probes target only the problem's own stack, with fake secrets |
| AI | Problems grade the code around the model, not the model, using scripted responses and fixed data. A skill that needs a real model goes to [ADR 0021](0021-ai-reviewed-problems.md) |
| Knowledge | Content that cannot be graded, such as compliance and incident response, fits non-autograded items |
| Staleness | Facts that go stale fast (model lineups, prices, deprecations) stay out of the catalog. Problems use invented values |
| Originality | Every problem is original ([ADR 0004](0004-original-problem-wording.md)) |

### Open to confirm

Recommended by the assistant. The owner took all seven as recommended when phase 1 started (2026-11-06), and each stays easy to change. R1 to R4 and R6 are built in phase 1; R5 and R7 apply to phase 2.

| # | Recommendation | Alternative | Trade-off |
|---|----------------|-------------|-----------|
| R1 | The six `domains` values above | Add `distributed-systems` for the system design items, or `software-design` for `lld` | A value with few rows is noise now. It can be added deliberately |
| R2 | The six `job_roles` values, with `general`, and the field name `job_roles`. `--role X` matches only rows listing `X`, so a security engineer's list stays short | `roles`, without `general`, with every role listed on every algorithm row | Listing all roles makes the filter useless; `roles` is shorter and collides |
| R3 | The mapping and overrides above | Only the mapping | The overrides make `--domain fintech` honest about banking; they and the bank projects are 13 rows of judgment, and 0214 to 0228 were the only ones the outline named |
| R4 | Store `scope`, with S24 checking it against `kind` and track. It is fully derivable from those today, so the check is what keeps it honest, and it stops being derivable when `system` projects arrive. Keep the value `function` | Derive it until the first `system` problem, skipping 270 lines; or name the value `unit`, which avoids `kind: function` | Storing costs a field that says nothing new today. Deriving means a later migration |
| R5 | The [content rules](#catalog-content-rules) | Allow exploit walkthroughs | Defensive-only keeps starters safe to ship in a public repository, and fits the sandbox of ADR 0019, which is a boundary for accidents |
| R6 | A label filter on `cstudy next` with no `--track` searches every track | Keep `next.tracks` | Otherwise the filter usually finds nothing, and the message would have to explain why |
| R7 | The language rule keyed on domains, and the first wave free of cryptography | `practical` in the subset tracks; or six languages from the start | See [Rule changes](#rule-changes). Six languages delays the catalog for a language order the owner has not asked for here |

## Phases

| Phase | Scope |
|-------|-------|
| 1 | Labels and backfill: the schemas, `domain/taxonomy.py`, S24 and its test; the one-pass backfill; `cstudy list`, `cstudy next`, the Problems view filters; catalog columns, with `scope` renamed `covers`; specs and guides (built) |
| 2 | The [first wave](#the-first-wave) of function-size problems, with the [rule changes](#rule-changes), in Python and TypeScript (built: `0255` to `0261`). A problem with any one of `security`, `identity` or `ai-llm` among its `domains` may list any subset of the languages that can express it; S13 is the only check this changes |
| 3 | Later waves. Project-size problems depend on [ADR 0019](0019-service-projects.md) (its P11); system-size ones need later design |

Phases 1 and 2 need no Docker and can run before ADR 0019 unless the owner orders otherwise. Each phase gets its docs and, at release, a website message.

## Consequences

- `cstudy list` and the page can answer "what is there for a security engineer", which no field does today.
- The catalog grows past 270, so counts in [catalog](../specs/catalog.md), [content](../specs/content.md), NFR-2 and NFR-3 change with phase 2. A problem in two languages costs NFR-3 less than one in six.
- A catalog problem may list fewer languages for a reason other than expressibility or the track, which is a real loosening of [ADR 0012](0012-go-and-rust.md).
- `meta.yaml` and `item.yaml` grow by three lines each, and `scope` is redundant until `system` projects exist (R4).
- The PRD's description and persona speak of one purpose, and change when phase 2 ships.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| A list passes about a dozen values, or authors keep asking for one more | Whether a closed list still serves |
| The first `system` problem is designed | `scope`'s check against `kind`, and ADR 0019's one-app assumption |
| Users ask for practice by domain, not just lists | A weakness group per domain in `cstudy next` |
| Domain-keyed language subsets outlast the first wave | Backfilling the other languages, or making the exception permanent |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| A `security` or `ai` track | A track says what type of practice this is. A security bug fix is `debugging`, and a security feature is `practical` |
| Free-form `tags` | Drifts into near-duplicates, and cannot be filtered or validated reliably. `patterns` is closed for the same reason |
| One `category` field | Domain, role and scope vary independently: a `security` problem can be for a `backend` engineer at any `scope` |
| Replacing `difficulty` with `scope` | A project can be easy and a function hard |
| Tracks as directories per domain | Slugs and paths would move, and a problem can have several domains |

## Amendment 2026-11-11: data, infrastructure, systems, software design and frontend

The decision above stands: three independent labels, closed lists, one change to a table, `DOMAINS`, `JOB_ROLES` and the schemas for each new value. This amendment records the values that [Revisit](#revisit) expected authors to ask for.

### Why

The catalog is for engineers from beginner to expert, and planned problems have no honest label. Data engineering (pipelines, streams, tables, quality, lineage), infrastructure as code, an architecture checker, and upcoming testing, refactoring, operating systems, networking, distributed systems and frontend problems would otherwise carry `backend` or `algorithms`, and `cstudy list --domain` could not answer "what is there for a data engineer". Three DSA topics also have no pattern of their own.

### What is added

| List | Value | Meaning |
|------|-------|---------|
| `domains` | `data` | Data engineering: pipelines, streams, tables, quality, lineage |
| `domains` | `infrastructure` | Infrastructure as code, configuration, deployment tooling |
| `domains` | `systems` | Operating systems, networking, distributed systems mechanics |
| `domains` | `software-design` | Testing, refactoring, design patterns, architecture |
| `domains` | `frontend` | Browser UI, state, rendering, accessibility |
| `job_roles` | `data-engineer` | Engineers who build and run data pipelines and tables. Named like `security-engineer`, `ai-engineer` and `ml-engineer` |
| `job_roles` | `frontend` | Engineers who build browser UIs. Named like the plain `backend` role |
| `patterns` | `sorting` | Sorting algorithms, custom orderings, sort-then-scan |
| `patterns` | `string-matching` | Substring search, rolling hashes, pattern and wildcard matching |
| `patterns` | `recursion` | Recursive decomposition and divide and conquer, without a search or a table |

The new values are appended, so the order of the existing ones does not change: the three patterns rank after `segment-tree-fenwick` in the `cstudy next` tie-break. Existing problems are not relabelled, and no new pattern has a problem yet, so the counts in [content](../specs/content.md#pattern-taxonomy) and [catalog](../specs/catalog.md) still describe 23 patterns in use.

### Language rule

S13 is unchanged except for one member of `LANGUAGE_SUBSET_DOMAINS`:

| Domain | Languages |
|--------|-----------|
| `data`, `infrastructure`, `systems`, `software-design` | All six, as for `algorithms`, `backend` and `fintech`. They are not in `LANGUAGE_SUBSET_DOMAINS`, so `_lists_every_language` requires every language that can express the problem |
| `frontend` | Any subset, because a browser UI problem is TypeScript first. It joins `security`, `identity` and `ai-llm` in `LANGUAGE_SUBSET_DOMAINS` in `domain/problem.py`, and the `must list` message names it |

### Where the values show

`cstudy next` validates `--domain` and `--role` against the module lists, `cstudy list` matches the labels of each entry as written, the session API gives them to the Problems view, whose filter menus are built from that answer, and both schemas list them. There is no display-name mapping: the CLI and the page show the ids. The [Revisit](#revisit) trigger "a list passes about a dozen values" is near, with 11 domains and 8 roles.
