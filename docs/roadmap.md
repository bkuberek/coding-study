# Roadmap

Each phase ends only when every exit criterion is observed. Phases run in order; content batches inside Phases 1 and 3 each pass the full verify gate before merging. The remaining work is planned as release milestones to [v1.0.0](#v100), then [v1.1](#v11) and [beyond](#beyond-11).

| Phase | Outcome | Main commands added |
|-------|---------|---------------------|
| 0 | Skeleton proves the editor workflow in all 4 languages | `doctor`, `start`, `test`, `solution`, `verify`, `list`, `show` |
| 1 | Daily practice loop plus DSA batch 1 | `done`, `next`, `hint`, `new` |
| 2 | Performance analysis | `bench`, `test --perf`, `verify --ladder` |
| 3 | DSA catalog complete (185) | none |
| 4 | Practical (progressive) and low-level design tracks | progressive support |
| 5 | Concurrency track | concurrent kind, `test --stress` and `--seed` for concurrent problems, `solution --broken` |
| 6 | System design, code review, debugging, behavioral | non-autograded items, buggy stubs |
| 7 | Progress polish | `stats`, `mock`, `export`, `import`, `test --stress` for oracle inputs, `test --json` |
| 8 | Project problems: Python, then TypeScript | project kind, `submit`, `status` |
| 9 | Local web UI with full practice parity | `serve`, `history`, `test --events` for every kind, `--json` for `list`, `next` and `doctor` |
| 10 | Async and concurrent project problems | harness operations, `new --virtual-clock` and `--stress`, `verify` S18 and D10 |
| 11 | Editor code intelligence in the web UI | `doctor` and `doctor --fix` for language servers; the `code_intelligence` and `autocomplete` preferences |
| 12 | Service projects | `dev`, `start --yes`, `list --needs`, `verify` S19 to S23 and D11 |

## Status

Phases 0 to 7 are implemented: every command in the table above exists with its tests, and the catalog holds 384 `ready` problems and 16 `ready` items. Exit criteria with recorded evidence are ticked in the phase sections. These validation items are still open:

| Item | Phase | Needs |
|------|-------|-------|
| LazyVim shows language-server diagnostics in a fresh stub for each language, without extra configuration | 0 | A manual editor check |
| IntelliJ imports a workspace's `jvm/` as a Gradle project with both subprojects | 0 | A manual editor check |
| At least 10 attempts through `next`, `start`, `test`, `done` | 1 | Real practice |
| `cstudy verify --oracle --ladder --require-ready` exits 0 over the whole catalog | 2, 3 | Ladder band fixes in progress; the oracle check already passes everywhere |
| Bench verdicts for 5 problems with an O(n^2) brute force, and their stability over 5 runs | 2 | A recorded run on an idle machine |
| Full `cstudy verify` (no oracle, no ladder) within the NFR-3 time | 3 | A recorded timing |

Each open item is a [v1.0.0 criterion](#release-criteria): P5, P6, C2, P4 and PF3.

## v1.0.0

v1.0.0 is the release in which every learner journey works end to end on macOS and Linux, proven by recorded runs and not only by tests, on a catalog in which every problem and guide has passed its gates. It is the first release under the compatibility promise below.

### Definition

Someone new to a topic installs cstudy on macOS or Linux, chooses the languages, job roles and domains they study, and runs the whole loop in the terminal, their own editor or the local page: learn from a guide, practise, test, review and come back on schedule. After setup, everything works offline, except the optional AI features, which use your own key. The journeys:

| Journey | Covers |
|---------|--------|
| Install and set up | Install, `cstudy init` with your languages, `cstudy doctor --fix` with every row ok |
| Learn | Read a guide, mark it read, follow a path |
| Practise | `next`, `start`, edit, `test`, `hint`, `done`, and the review comes back |
| Levels and projects | `test`, `submit`, levels opening, `done` with level passes |
| Service projects | Start with Docker, the dev stack, `test`, `submit`, nothing left behind |
| Frontend problems | A React component graded in a headless browser in the sandbox |
| Optimality | `bench` gives a verdict with a confidence level |
| Progress | `stats`, `history`, `mock`, sets |
| Back up and move | Export and import, or clone the workspace and run `doctor --fix` |
| Upgrade | A newer 1.x migrates the workspace and progress after a backup, and nothing is lost |
| Your own problems | `new`, `verify --require-ready`, and the problem joins `next` |
| AI preview | With your own key: the assistant in a drawer on every page, problem sessions on an attempt, AI review of rubric-checked problems |

At 1.0 the catalog holds about 427 problems (the 16 former items among them), 185 guides and 28 paths.

### Compatibility promise

The promise starts at 1.0.0. Before it, any release may change any surface.

| Surface | 1.x promise |
|---------|-------------|
| CLI commands, flags and exit codes | Public. None is removed, renamed or given a new meaning; new ones are additive |
| `--json` documents | Public, additive only: fields are never removed, renamed or retyped, and each document has a published JSON Schema |
| `--events` stream | Public, versioned: `version` 1 changes only with an incompatible change, and readers ignore unknown event types and fields |
| Workspace layout outside `.cs/` | Public. A 1.0 workspace works with every 1.x. A layout change bumps the marker's `schema` and `cstudy doctor --fix` migrates it; an older cstudy refuses a newer schema |
| `progress.db` | Public in behaviour: every 1.x migrates any earlier 1.x database forward, automatically, after a backup. No downgrade. The tables are not an API for other programs, except the assistance and AI review records, which are public records |
| Progress export | Public: any 1.x imports any earlier 1.x export |
| Config keys and environment variables | Public: keys and meanings stay; a default may change in a minor release, with a release note |
| Your own problems | Public, additive only: a problem that passes `cstudy verify` under 1.0 loads, runs and verifies under every 1.x. New checks apply to catalog content only |
| Canonical IDs | A released content ID never changes, since progress is keyed on it. Content itself may be corrected or reworded in any release |
| Web API, `.cs/`, guide and path formats | Internal: they may change in any release |
| Human-readable output | Not promised: scripts use `--json` |
| AI features | Preview: their commands, `[ai]` keys and behaviour may change in a minor release. The assistance record and AI review records are public |
| Kotlin code intelligence | Preview: it depends on builds outside cstudy that expire |

Rules:

- **Breaking changes** ship only in 2.0. A breaking change makes a 1.x script, workspace, database, export, config file or problem of your own stop working or change meaning.
- **Minor releases** add commands, flags, fields, event types, config keys, problem-format fields, languages and content. **Patch releases** fix bugs and correct content.
- **Deprecation**: a deprecated public flag, key or field keeps working until 2.0 and warns on stderr, never in `--json` or `--events` output.
- **Toolchain and platform floors** (Python, Node, the JDK, Go, Rust, Docker Engine, OS versions) may rise in a minor release when upstream support ends, announced one minor release ahead.
- **Support**: fixes land on the latest 1.x minor release.

### Release criteria

Status is **met**, **partly met** or **not met**; not met includes criteria that need a recorded run that does not exist yet. Each criterion names the milestone that closes it.

| Area | Met | Partly met | Not met |
|------|----:|-----------:|--------:|
| Compatibility and release engineering | 1 | 2 | 6 |
| Product | 0 | 1 | 7 |
| AI preview | 0 | 0 | 9 |
| Content | 1 | 2 | 6 |
| Platforms and install | 0 | 3 | 4 |
| Reliability | 1 | 0 | 3 |
| Docs | 0 | 2 | 1 |
| Accessibility | 2 | 1 | 1 |
| Performance | 1 | 1 | 2 |
| Security and sandbox | 0 | 2 | 3 |
| Licensing | 2 | 3 | 0 |
| Privacy and offline | 2 | 2 | 1 |
| **Total (72)** | **10** | **19** | **43** |

#### Compatibility and release engineering

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| E1 | A compatibility spec and an ADR state the public, internal and preview surfaces, breaking changes, deprecation and the support window | Not met | v0.51 |
| E2 | Contract tests: a snapshot of commands, flags and exit codes; a JSON Schema per `--json` document; snapshots of the config keys and the workspace marker | Partly met: the event and web API schemas are validated | v0.51 |
| E3 | Canonical IDs `<type>/<slug>` for all content; numeric problem IDs and the ID column are gone and folders are `problems/<slug>`; the 16 items are problems of the kinds `system-design` and `code-review`, checked by a rubric; the Problems page has a Checked by column (tests, rubric, plus AI review) | Not met | v0.51 |
| E4 | Every migration takes a backup first; upgrade tests migrate a fixture of each schema from 1.0 forward; export round trips keep every row | Partly met: one upgrade path is tested, and migrations run in place with no backup | v0.51 |
| E5 | Curated release notes for each minor release: highlights, upgrading, deprecations | Not met | v0.62 |
| E6 | Release candidates are tagged without reaching the Homebrew tap, and only fixes land during the soak | Not met | v0.62 |
| E7 | Rollback is documented and drilled once: install the previous version, then restore from the backup or an export | Not met | v0.62 |
| E8 | `UPGRADING.md` covers moving from 0.x to 1.0 | Not met | v0.51 (draft), release candidates (final) |
| E9 | 1.0.0 is cut deliberately with a major bump | Met: `semantic-release version --major` | v1.0.0 |

#### Product

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| P1 | A learner profile of languages, job roles and domains, each defaulting to all, sets the default filters on every page; a page's filter can widen them without editing the profile; one shared filter component serves every page | Not met | v0.52 |
| P2 | Languages decide which workspace folders exist: `cstudy init --lang`, `cstudy lang add`, and `doctor`, `doctor --fix` and the IDE files scoped to the chosen languages; a fresh workspace with one language gets an all-ok `doctor` | Not met | v0.52 |
| P3 | Every journey of the [definition](#definition) passes in the terminal, and on the page where the page has it | Partly met: the parity end-to-end test covers practice for every kind in all six languages | Release candidates |
| P4 | `bench` is honest: on 5 problems with an O(n²) brute force, the brute force gets `suboptimal` at medium or high confidence in every language, the optimal reference gets `optimal`, and the verdicts hold in 5 runs out of 5 | Not met | v0.54 |
| P5 | Editor checks: LazyVim shows language-server diagnostics in a fresh stub per language, and IntelliJ imports `jvm/` with both subprojects | Not met | v0.54 |
| P6 | Real use during the soak: at least 30 finished attempts across at least 4 languages and every kind, in both the terminal and the page, with no open P1 issue | Not met | Release candidates |
| P7 | The desktop app is designed: an accepted ADR for `cstudy app` and `cstudy app install` | Not met | v0.62 |
| P8 | Feedback and issue reporting: GitHub issue forms in `.github/ISSUE_TEMPLATE` for a bug, missing content or a feature, and a content error in a problem or guide; "Found an issue?" and "Missing something?" entries in the page, one global and one on every problem and guide page, open the matching form in the browser, prefilled through query parameters with the cstudy version, the OS, the page and the content ID (`<type>/<slug>`), never with code or transcripts; `cstudy feedback` does the same from the terminal | Not met | v0.53 |

#### AI preview

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| AI1 | Bring your own key: keys only in `credentials.toml`, never in the workspace, logs, transcripts or exports; consent before the first send per provider, model and purpose; a daily token cap; usage and known cost shown | Not met | v0.59 |
| AI2 | Routing: one fixed model, or auto, which serves each task from a fast or a strong tier you configure | Not met | v0.59 |
| AI3 | AI review of rubric-checked problems: a schema-validated verdict per rubric criterion, stored as a versioned record with provider, model and rubric version, labelled AI review, never changing a grade or the schedule | Not met | v0.59 |
| AI4 | The chat drawer on every page, with free sessions you create, rename, archive, compact and delete, and the same sessions in `cstudy ai chat`; the drawer is a chunk with its own bundle budget | Not met | v0.60 |
| AI5 | Web search through each provider's server-side search tool, per message, counted in usage | Not met | v0.60 |
| AI6 | Problem sessions: one per `attempt_id`, read-only once the attempt is done or aborted; help modes `interviewer`, `collaborator` and `tutor`; during `cstudy mock`, interviewer only, with free sessions locked | Not met | v0.61 |
| AI7 | Each turn gets a tag; a versioned assistance record is stored on the attempt, caps the review grade, and shows in `cstudy history`, `cstudy stats` and the page | Not met | v0.61 |
| AI8 | With AI off, nothing leaves the machine and every other feature works as before | Not met | v0.59 |
| AI9 | The assistant notices when a message sounds like a bug or a missing feature, offers to draft the issue, shows the draft, and opens the prefilled form of P8 only after you agree. cstudy holds no GitHub token; you submit the issue on GitHub | Not met | v0.60 |

#### Content

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| C1 | `cstudy verify --oracle --require-ready` exits 0 over the whole catalog on the release-candidate commit | Partly met: the oracle check passes everywhere, with no run recorded for a release candidate | v0.54, release candidates |
| C2 | `cstudy verify --ladder --require-ready` exits 0 over the whole catalog | Not met | v0.54 |
| C3 | Every guide passes its checks, and every path has a review record with checked citations | Partly met: the paths on main have records | v0.54, then each content milestone |
| C4 | The `related` rule is settled, symmetric where the spec requires it, and enforced by a static check | Not met | v0.54 |
| C5 | A problem that links a guide is a step of a path that holds that guide, unless exempted, enforced by a `verify` check; the paths that open on a hard problem open on an easy one or a `level: 1` step | Not met | v0.54 |
| C6 | The counts agree across the README, this roadmap and the catalog | Met | Kept in every milestone |
| C7 | The content must-haves below, each passing C1 to C3 | Not met | v0.55 to v0.57 |
| C8 | Browser-graded React problems: the grader of [Phase 16](#phase-16-frontend-problems) and two problems on it | Not met | v0.58 |
| C9 | Guides carry `job_roles` and `domains` labels, checked by `cstudy verify` | Not met | v0.52 |

The content must-haves:

| Must-have | Guides | Problems | Milestone |
|-----------|-------:|---------:|-----------|
| DSA foundations path: complexity analysis, linked lists, sorting, bit manipulation, matrices and number tricks; the unlinked DSA problems linked | 5 | 0 | v0.55 |
| Debugging, git and code reading path, with the debugging track as its steps | 7 | 0 | v0.55 |
| Backend services path: HTTP API design, validation and errors, schema design and migrations, background jobs and queues, caching, rate limiting; the unlinked backend problems linked | 6 | 0 | v0.55 |
| Advanced DSA guides: minimum spanning trees and bridges, range queries, string matching | 3 | 0 | v0.55 |
| Applied SQL and database on-ramps: SQL problems graded against Postgres, and problems for the LSM and page guides | 2 | 5 | v0.56 |
| System design path, with system-design problems as its steps, opening on an easy one | 5 | 2 | v0.56 |
| Software design path, with the low-level design problems as its steps | 5 | 0 | v0.56 |
| Concurrency and async path, with an easy problem and a worker pool on channels | 4 | 2 | v0.56 |
| Frontend fundamentals path on today's engine | 6 | 3 | v0.57 |
| Platform and operations path: containers, CI/CD and deploys, logs, metrics and traces, SLOs and alerting, incidents | 5 | 2 | v0.57 |
| Entry problems for the networking, distributed systems, OS, data engineering and testing paths, and a mutation tester | 0 | 6 | v0.57 |
| Machine learning depth: trees and ensembles, clustering and nearest neighbours, neural network basics | 3 | 3 | v0.57 |
| Security: password storage and sessions, encryption and signatures | 2 | 2 | v0.57 |
| Browser-graded React problems: the search box, and a data table with sorting and pagination | 0 | 2 | v0.58 |
| **Total** | **53** | **27** | |

#### Platforms and install

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| PL1 | A published support matrix: macOS on Apple Silicon and Linux x86_64 and arm64 with glibc (Ubuntu 24.04 the reference) supported and verified; Windows through WSL2 documented, not verified; native Windows unsupported | Not met | v0.53 |
| PL2 | A macOS gate for every release candidate: install from its artifacts, `init`, `doctor --fix`, one problem per language, one service project, a browser-graded problem, and the page in Safari | Not met | v0.53, then every release candidate |
| PL3 | A Linux gate for every release candidate: a fresh install from its artifacts in a clean container, the wheel with its requirements file and the Homebrew formula on Linux, then the same journey as PL2 | Partly met: the full local gates run on Linux | v0.53, then every release candidate |
| PL4 | A "Run on Windows with WSL2" guide, with the warning that cstudy is not tested on Windows or WSL | Not met | v0.53 |
| PL5 | The install docs pin versions: uv and pipx install from a version tag, and Homebrew from the tap | Partly met: uv and pipx build the default branch | v0.53 |
| PL6 | A policy for how the toolchain floors move in 1.x | Partly met: the floors are documented, the policy is not | v0.53 |
| PL7 | A fresh-eyes run of the README and the Getting started path on clean macOS and Linux machines, with every stumble fixed | Not met | v0.53 |

#### Reliability

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| R1 | The full local gate passes twice in a row on the release-candidate commit, with no reruns | Not met | v0.50 (hardening), release candidates |
| R2 | CI is green on main for the release candidate and throughout the soak | Not met | Release candidates |
| R3 | No internal error (exit 70) during the soak | Not met | Release candidates |
| R4 | The docs state what CI runs and what stays a local gate | Met | |

#### Docs

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| D1 | The normative docs match what shipped | Partly met: the PRD's scope and platforms match this plan; the docs index and the progress spec lag | v0.51, then each milestone |
| D2 | In-app docs: `cstudy docs`, a Docs page, and a test that parses every command and flag the docs show against the real CLI | Partly met: in progress | v0.50 |
| D3 | A guide to the AI preview: keys, providers, what is sent, costs and caps | Not met | v0.61 |

#### Accessibility

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| A1 | axe-core finds no WCAG 2.2 A or AA violation on any view or dialog, in light and dark, at 1440 and 390 pixels, in Chromium, Firefox and WebKit | Met locally; CI runs Chromium | Every release candidate |
| A2 | The keyboard-only journey passes | Met | |
| A3 | A manual screen-reader pass of the learn and practise journeys with VoiceOver and Orca, with its findings fixed | Not met | v0.62 |
| A4 | Every new view and control (Guides search, example tabs, the Docs page, the profile filters, the AI drawer) is covered by A1 and A2 | Partly met: covered as each lands | Each milestone |

#### Performance

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| PF1 | NFR-1's warm `cstudy test` p50 per language, recorded on the release candidate on Linux and macOS | Partly met: measured on 0.x | v0.54, release candidates |
| PF2 | NFR-2 at the 1.0 catalog size | Not met | v0.54 |
| PF3 | NFR-3: a recorded full `verify --require-ready` at the 1.0 catalog size, with the budget revised to it | Not met | v0.54 |
| PF4 | NFR-11 and NFR-12, with a budget for each new chunk | Met | Kept in every milestone |

#### Security and sandbox

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| S1 | An independent security review of `cstudy serve`, the code-intelligence broker, the sandbox, the browser grader and the AI features, with a threat model and its findings closed | Partly met: the controls are specified and tested | v0.62 |
| S2 | A clean dependency audit of `uv.lock`, the web UI lock, the language-server manifest and the pinned images | Not met | v0.62, release candidates |
| S3 | Rootless Docker and SELinux proven or documented as unsupported | Not met | v0.62 |
| S4 | A written trust model for problems from others: generators, oracles, checkers and native code run as you, with no sandbox | Not met | v0.62 |
| S5 | `SECURITY.md` states the 1.x support window | Partly met | v0.62 |

#### Licensing

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| L1 | `cstudy about --credits` and `--licenses` list every component cstudy redistributes or downloads, the vendored Rust crates, the vendored Go module and the images included | Partly met | v0.62 |
| L2 | The Kotlin language server has explicit acceptance, a preview label and handled expiry | Partly met: acceptance and expiry exist | v0.62 |
| L3 | Every image a problem pulls is pinned by digest, its licence recorded, and none is under a licence that is not open source | Partly met: digests are enforced | v0.62 |
| L4 | Code and content under MIT, in original wording, with sources recorded | Met | |
| L5 | Terms that bind the user are disclosed | Met | |

#### Privacy and offline

| ID | Criterion | Status | Milestone |
|----|-----------|--------|-----------|
| O1 | No telemetry and no update check, enforced by a test | Partly met: neither exists; no test guards it | v0.62 |
| O2 | A published network map: each command that can use the network, and why | Partly met: spread across the specs | v0.62 |
| O3 | Offline proof: after setup, the learn, practise and levels journeys and a page run pass with networking off | Not met | v0.62 |
| O4 | The page requests nothing off the machine | Met | |
| O5 | User code sees only the allowlisted environment | Met | |

### Milestones

Each milestone is one release behind the full local gate. Sizes count working days, not calendar waits such as overnight runs or the soak: **S** at most a day, **M** 2 to 5 days, **L** more than a week.

| Milestone | Contents | Size |
|-----------|----------|------|
| v0.49 | Guide paths on database internals, infrastructure as code and knowledge representation, with their review records (C3): 132 guides and 20 paths | S (in progress) |
| v0.50 | Guides page search and filters; example tabs; in-app docs with `cstudy docs`, the Docs page and the parsed docs test (D2); hardening of load-sensitive tests (R1); A4 and PF4 for the new UI | M (in progress) |
| v0.51 Compatibility contract | The compatibility spec and ADR (E1); canonical IDs `<type>/<slug>`, `problems/<slug>`, the 16 items as `system-design` and `code-review` problems checked by a rubric, and the Checked by column (E3); contract tests (E2); a backup before every migration, the upgrade test matrix and export round trips (E4); a deprecation helper; the docs pass (D1); a draft `UPGRADING.md` (E8) | L |
| v0.52 Learner profile | Languages, job roles and domains as default filters on every page, widened per page, through one shared filter component (P1); `cstudy init --lang`, `cstudy lang add`, and `doctor` and the IDE files scoped to the workspace's languages (P2); `job_roles` and `domains` on guides with their `verify` check (C9); A4 for the profile and filters | L |
| v0.53 Platforms | The support matrix and the toolchain-floor policy (PL1, PL6); version-pinned install docs (PL5); the shared smoke script and the first recorded macOS and Linux gates (PL2, PL3); the WSL2 guide (PL4); the fresh-eyes onboarding run (PL7); the issue forms, the page's feedback entries and `cstudy feedback` (P8) | L |
| v0.54 Content bar | Recorded oracle and ladder runs over the catalog, with the bands fixed (C1, C2); bench stability (P4); the `related` rule and the path-step check, with the existing gaps closed (C4, C5); review records (C3); the editor checks (P5); NFR timings (PF1 to PF3). The [Status](#status) table closes | L, mostly overnight runs on an idle machine |
| v0.55 Content batch 1 | DSA foundations, debugging and code reading, backend services and advanced DSA: 21 guides, 3 paths and about 100 link edits (C7) | L |
| v0.56 Content batch 2 | Applied SQL, system design, software design, concurrency and async: 16 guides, 3 paths, 9 problems (C7) | L |
| v0.57 Content batch 3 | Frontend fundamentals, platform and operations, entry problems, machine learning, security: 16 guides, 2 paths, 16 problems (C7) | L |
| v0.58 Frontend problems | [Phase 16](#phase-16-frontend-problems): the ADR and spike, a browser image in the sandbox, the grader that drives it, `cstudy dev` for it, and the React search box and data table (C8) | L |
| v0.59 AI foundation | An ADR that amends [ADR 0021](decisions/0021-ai-reviewed-problems.md); the model port and four provider adapters; keys, consent, caps and usage (AI1); fixed and auto routing (AI2); the AI settings section; AI review of rubric-checked problems (AI3); nothing sent with AI off (AI8) | L |
| v0.60 AI chat | Sessions in `progress.db`; replies as child `cstudy ai reply --events` processes relayed to the page; the drawer chunk and its budget; free sessions and `cstudy ai chat` (AI4); page context; web search (AI5); issue drafts from the assistant (AI9) | L |
| v0.61 AI problem sessions | Problem sessions, help modes and the mock rules (AI6); turn tags, the assistance record, its grade caps, and its place in history, stats, export and import (AI7); the AI preview guide (D3); the PRD's AI requirements | L |
| v0.62 Hardening | The security review and threat model (S1); the dependency audit (S2); rootless Docker and SELinux (S3); the trust model (S4); `SECURITY.md` (S5); the network map, the telemetry guard and the offline test (O1 to O3); licensing (L1 to L3); the screen-reader pass (A3); the release-notes template, release-candidate tags and the rollback drill (E5 to E7); the desktop app ADR (P7) | L |
| v1.0.0-rc.1 to rc.n | Feature freeze; the macOS and Linux gates on every candidate (PL2, PL3); a 14-day soak with real use (P6), CI green (R2) and no exit 70 (R3); the journey checklist (P3); two clean full gates in a row (R1); final runs of C1, A1, PF1 and S2; curated notes and the final `UPGRADING.md` (E8). | M, plus 14 days |
| v1.0.0 | Every criterion met; the major bump (E9) | S |

**AI preview rules** that v0.59 to v0.61 build:

- Help caps the review grade: light help caps it at `ok`, heavy help at `hard`, and a full answer gives `again`. An assisted attempt still counts as passed; the schedule brings it back sooner.
- A turn that could not be tagged counts as light help and shows as untagged in the record.
- During `cstudy mock`, the assistant runs only in `interviewer` mode; hints are allowed and recorded, and free sessions stay locked until the mock ends.
- A free session on another page during an attempt is allowed, with a reminder and a one-click move into the problem session.
- `cstudy export` leaves out transcripts unless `--with-transcripts` is given; assistance records and AI reviews are always included.

**Order.** The contract comes first, so every later change is measured against it and new content uses canonical IDs. The profile comes before the platform gates, so the gates exercise the final `init` and `doctor`, and before the content batches, so new guides carry their labels. The content batches and the frontend grader can be built alongside the AI milestones and ship in whichever release is ready first, so the version numbers are an order, not a promise. Hardening comes last before the freeze, so the security review sees the code that ships.

**Estimate.** About 14 to 18 weeks from v0.50 to v1.0.0, which puts v1.0.0 between late February and late March 2027, if the content batches are built alongside the engineering milestones; built one after another, add about four weeks. The engineering milestones set the pace:

| Stretch | Weeks |
|---------|------:|
| v0.50 to v0.54: contract, profile, platforms, content bar | 5 to 6 |
| v0.58: the browser grader and React problems | 2 to 3 |
| v0.59 to v0.61: the AI preview | 4 to 5 |
| v0.62: hardening | 1 to 1.5 |
| Release candidates and the 14-day soak | 2.5 |

## v1.1

Two additions, each additive to the 1.0 promise.

| Addition | Contents | Size |
|----------|----------|------|
| Desktop app (preview) | `cstudy app` opens the page in its own window over the same server, assets and API as `cstudy serve`, which stays the reference way in. `cstudy app install` sets up its own dependencies without sudo, in an environment cstudy owns: pyobjc on macOS, Qt WebEngine wheels on Linux, and Edge in app mode under WSL2. It writes a launcher per platform, and closing the window stops everything the server started. The app never gets a page feature the browser lacks, and a smoke test per platform covers it. Its flags become stable after one minor release as a preview | L |
| WSL2 verification | A smoke test inside WSL2 on a local Windows VM for every release candidate: install, `init`, `doctor --fix`, a problem per language, the page from a Windows browser, a service project on Docker Desktop's WSL 2 backend, export and import, and an upgrade. `cstudy serve --open` opens a Windows browser, and a `wsl` doctor row warns about a workspace under `/mnt/`. The WSL2 guide drops its warning | M |

## Beyond 1.1

**Later 1.x minor releases** add without breaking the promise:

- [Phase 17](#phase-17-infrastructure-tools-in-the-sandbox): real infrastructure tools in the sandbox.
- [Phase 12](#phase-12-service-projects) P14: Rust service projects.
- [Phase 10](#phase-10-async-and-concurrent-project-problems): the async pilot problems.
- AI: narrative summaries of finished problem sessions, the simulated interview and the whiteboard of [Phase 14](#phase-14-ai-reviewed-problems), and a local model.
- Content: more system-design and code-review problems, paths on information retrieval and on compilers, six-language ports of the Python and TypeScript problems, and more entry steps in the advanced DSA patterns.
- Format extensions: grading tests the learner writes, maps in the type DSL, `bench --json` and `verify --json`.
- Native Windows, which needs its own process control, file locks, paths, runners and sandbox mounts.

**2.0** is reserved for breaking changes to a public surface. None is planned; deprecations collected during 1.x are removed there.

## Phase 0: Skeleton

**Scope.** CLI with hexagonal layout; JSON Schemas; type DSL parser; 4 stub generators; Python, TypeScript and JVM runners; conformance suite; workspace projects (uv, pnpm, Gradle wrapper with Java and Kotlin subprojects); reference materialization; all six comparators; `progress.db` with the `attempts` and `test_runs` tables (active-attempt tracking); generated cases; `--oracle`; hang guard; per-case timing; optional time limits with calibration. Three problems end to end in all 4 languages:

| Problem | Proves |
|---------|--------|
| `two-sum` | arrays, `unordered` comparator, generator, oracle, opt-in TLE for brute force |
| `invert-binary-tree` | `TreeNode` input and output serialization |
| `lru-cache` | class kind, operation sequences, `ops` comparator |

**Exit criteria.**

- [x] `cstudy doctor` reports all checks ok on a macOS development machine.
- [x] `cstudy verify --conformance` passes in all 4 languages (every DSL type round-trips; every error path reported correctly).
- [x] `cstudy verify --oracle --require-ready` exits 0 for the 3 problems.
- [ ] Manual run per language in LazyVim: `cstudy start`, failing `cstudy test`, fix, passing `cstudy test --watch`; LSP diagnostics work in the stub without extra configuration.
- [ ] IntelliJ imports a workspace's `jvm/` as a Gradle project with both subprojects and runs nothing extra.
- [x] Warm `cstudy test` p50 over 10 runs is recorded per language and meets NFR-1, or the gap is recorded against PRD Q4.
- [x] Time limits are off by default; with `--time-limit`, a brute-force `two-sum` fails `g1` with `TLE` in all 4 languages while the hash-map approach passes.
- [x] An infinite loop is reported `TIMEOUT` and the remaining cases still run.
- [x] Domain unit tests pass; the import-linter contract passes.

## Phase 1: Practice loop and DSA batch 1

**Scope.** `schedule` table migration; `cstudy done`, `cstudy next`, `cstudy hint`; status columns in `cstudy list`; `--fresh`, archive and `--timer`; `cstudy new` with the 4 templates; content batch 1 (arrays-hashing, two-pointers, sliding-window, stack: 34 problems).

**Exit criteria.**

- [x] Scheduler unit tests reproduce the worked sequence in [progress-and-scheduling](specs/progress-and-scheduling.md#scheduling-algorithm).
- [x] `cstudy next` is deterministic: same database snapshot, date and flags give the same result (property test).
- [x] `cstudy new` output for each template passes `cstudy verify --static` after replacing placeholders.
- [x] Batch 1: `cstudy verify --changed --oracle --require-ready` exits 0.
- [ ] At least 10 attempts are completed through `next`, `start`, `test`, `done`.

## Phase 2: Performance analysis

**Scope.** `cstudy bench`, `cstudy test --perf`, `bench_runs`, per-runtime memory metrics, `cstudy verify --ladder`, the scheduling penalty for suboptimal verdicts.

**Exit criteria.**

- [ ] `cstudy verify --ladder` passes for all Phase 0 and Phase 1 problems.
- [ ] For 5 chosen problems with an O(n^2) brute force, the brute force benched as the user's code gets `suboptimal` at confidence medium or high in all 4 languages, and the optimal reference benched as the user's code gets `optimal`.
- [ ] Stability: benching the same code 5 times yields the same verdict 5 out of 5 times for those problems.
- [x] Bench output never prints a percentile and always prints a confidence level.

## Phase 3: DSA catalog

**Scope.** Batches 2 to 6 from [content](specs/content.md#content-batches).

**Exit criteria.**

- [ ] 185 `ready` DSA problems; `cstudy verify --oracle --ladder --require-ready` over all exits 0.
- [ ] Full `cstudy verify` (no oracle, no ladder) meets NFR-3.

## Phase 4: Practical and low-level design

**Scope.** Progressive support (level unlock, statement rendering per level, `--level`); 6 practical and 8 LLD problems with rubrics.

**Exit criteria.**

- [x] A progressive problem unlocks levels one at a time in all 4 languages and hides locked levels from the rendered statement.
- [x] All 14 problems `ready` and passing the gate.

## Phase 5: Concurrency

**Scope.** A spec amendment that settles the stress-scenario schema and PRD Q5 and Q6 ([problem-format](specs/problem-format.md#concurrent-problems), [runners](specs/runners.md#concurrent-jobs), [ADR 0006](decisions/0006-concurrency-stress-testing.md)), then runner support with the stress conformance fixtures, and the 6 problems in [content](specs/content.md#concurrency-problems).

**Exit criteria.**

- [x] Amendment merged before any runner work starts.
- [x] `cstudy verify --conformance` passes in all 4 languages, including the stress fixtures `9014` to `9019`.
- [x] A deliberately unsynchronized reference fails its stress case in at least 9 of 10 runs per supported language; the correct reference passes 10 of 10 (`cstudy verify` D6 and D7, for every concurrent problem).
- [x] 6 problems `ready`.

## Phase 6: System design, code review, debugging, behavioral

**Scope.** `tracks/` items with `item.yaml`, notes templates, `cstudy solution` for references and rubrics; `stub: buggy`; `tracks/behavioral/README.md` on preparing from your own story bank.

**Exit criteria.**

- [x] 10 system design and 6 code review items `ready`; 8 debugging problems `ready`.
- [x] `cstudy next --track system-design` and `cstudy done` work for non-autograded items.

## Phase 7: Progress polish

**Scope.** `cstudy stats`, `cstudy mock`, `cstudy export` and the `cstudy import` that restores it, `cstudy test --stress` for non-concurrent kinds (generated inputs against the oracle), `cstudy test --json`; decision on a persistent JVM runner (PRD Q4) from Phase 0 to 6 latency data.

**Exit criteria.**

- [x] `cstudy stats` matches hand-computed values on a fixture database.
- [x] `cstudy export` output re-imports into an empty database with identical `cstudy stats` output.
- [x] PRD Q4 closed with a recorded decision.

## Phase 8: Project problems

**Scope.** [ADR 0014](decisions/0014-project-problems.md) and its spec amendments, then the project kind ([problem-format](specs/problem-format.md#project-problems)): project folders, generated native tests, the `suite` and project grading jobs ([runners](specs/runners.md#project-jobs)), `cstudy submit` and `cstudy status`, verify checks S14 to S16 and D9. 8a is the Python pilot `0249-bank-project-python`, playable from `start` to `done`; 8b the TypeScript pilot `0250-bank-project-typescript` and `node:test` through the same suite protocol. Later, each behind its own spike: web interface groundwork in the CLI (an event stream, a starter manifest with `cstudy start --restore`, a lock per project), Java and Kotlin projects (K4: 8c `0251-bank-project-java`, 8d `0252-bank-project-kotlin`), and Go and Rust projects (K5, K6: 8e `0253-bank-project-go`, 8f `0254-bank-project-rust`).

**Exit criteria.** Each pilot passes three checks in its language: `cstudy verify --conformance` passes with the language's project and suite fixtures, and `cstudy verify <slug> --require-ready` exits 0; a manual run through all four levels, from `cstudy start` to `cstudy done`; and the warm p50 of `cstudy test` and of `cstudy submit` is within the language's NFR-1 target.

- [x] 8a, Python, `bank-project-python`: fixtures 9022 and 9024; NFR-1 1.0 s.
- [x] 8b, TypeScript, `bank-project-typescript`: fixtures 9023 and 9025; NFR-1 1.0 s.
- [x] 8c, Java, `bank-project-java`: fixtures 9026 and 9028; NFR-1 3 s.
- [x] 8d, Kotlin, `bank-project-kotlin`: fixtures 9027 and 9029; NFR-1 5 s.
- [x] 8e, Go, `bank-project-go`: fixtures 9030 and 9031; NFR-1 2 s (1.5 s until 0.9.0). Its warm p50 was 1.2 to 1.4 s when ADR 0014 measured it and is 1.6 to 1.7 s before 0.9.0 (see Phase 9).
- [x] 8f, Rust, `bank-project-rust`: fixtures 9032 and 9033; NFR-1 2 s.

## Phase 9: Local web UI

**Scope.** [ADR 0015](decisions/0015-local-web-ui.md) and its specs ([web-ui](specs/web-ui.md), [cli](specs/cli.md#cstudy-serve)). First the CLI surface the page needs: `cstudy test --events` for every kind ([event stream](specs/cli.md#event-stream)), `--json` for `cstudy list`, `cstudy next` and `cstudy doctor`, `cstudy list --kind`, `cstudy status` for every kind and `cstudy history`. Then `cstudy serve`: the server with its security model, the vendored CodeMirror 6 front end, the read API and page shell, saving and file management, runs with live results and diagnostics, attempt flows (start, hints, solutions, done), mock interviews, notifications, progress and health views, and diagnostic parsers for `javac`, `kotlinc`, `go` and `cargo`. The first runnable slice is a project problem: `cstudy serve --open`, edit and save a file, run the tests and submit with streamed results, cancel a run, see an import error marked on its line, and watch a level open.

**Exit criteria.**

- [x] Every practice command in the [parity table](specs/web-ui.md#command-parity) works from the page, for every kind, in all six languages: the API tests cover every endpoint, and `test_serve_parity_end_to_end.py` starts one problem of each kind (function, design, progressive, concurrent, a debugging problem, project) in each language, runs its tests in the child `cstudy test --events` and finishes it with Done through the page's API, 36 rows (216 tests in 67 s).
- [x] The API security tests pass: Host, Origin, cookie, CSRF, CSP and the absence of CORS headers, body limits, and every file API path rule (NFR-10).
- [x] Every API response validates against its schema, and the documents the CLI also prints equal its `--json` output.
- [ ] The browser smoke test passes in headless Chromium: login, the editor under the CSP, a streamed run, cancel, a diagnostic marker, the solution confirmation, Vim loading, no console error; a manual check passes in Safari and Firefox. Every browser test passes in Playwright's Chromium, Firefox and WebKit (Safari's engine), the diagnostic marker included (`test_browser_diagnostics.py`). Open: the manual check in the Safari app is pending.
- [x] Warm page runs meet NFR-11 on a quiet machine for the six project pilots and one single-file problem per language: every page run is within 0.1 s of its terminal run ([feedback](specs/web-ui.md#feedback)). Measured before the release on an Apple Silicon Mac at load averages 3.4 to 5.5: the Go project's terminal p50 of 7 is 1.64 to 1.74 s (v0.8.0: 1.61 to 1.65 s), within NFR-1's Go project target, raised from 1.5 s to 2 s for 0.9.0; the Rust project 0.98 s, the Python project 0.64 s, `two-sum` in Go 0.78 s and in Python 0.58 s are within theirs.
- [x] The bundle meets NFR-12, its rebuild matches `manifest.json`, and the wheel holds every asset.
- [x] A user guide, `docs/guides/web-ui.md`, covers starting the server, the views and the keyboard.

## Phase 10: Async and concurrent project problems

**Scope.** [ADR 0017](decisions/0017-async-project-problems.md) and its spec amendments ([problem-format](specs/problem-format.md#asynchronous-code-and-the-virtual-clock), [runners](specs/runners.md#virtual-clock-and-stress-in-project-jobs), [authoring](specs/authoring.md#what-cstudy-verify-checks), [cli](specs/cli.md#cstudy-new)): `async` methods, `project.clock: virtual` and its harness operations `@advance`, `@spawn`, `@join` and `@now`, `stalled` project cases, generated tests on the virtual clock, checks S18 and D10, `cstudy new --virtual-clock`, stress cases and broken overlays in projects, and Go 1.25. One language family per step, each proved by a pilot problem before the next starts: 1 the Go virtual clock, 2 Python and TypeScript asynchronous methods, 3 stress cases in all six languages, 4 Kotlin coroutines (spike K7), 5 Rust async on tokio (spike K8).

**Exit criteria.** A step ends when its runner passes `cstudy verify --conformance` with its fixtures, `cstudy verify <slug> --require-ready` exits 0 for its pilot, and a manual run through all its levels, from `cstudy start` to `cstudy done`, works.

- [x] The ADR is accepted and the specs amended before any runner work starts.
- [x] Step 1, Go, tooling: fixture 9034 (`9034-conformance-project-clock-go`) passes, with its `advance` and `spawn-join` cases also run as generated `synctest` tests; a project scaffolded by `cstudy new --virtual-clock` passes `cstudy verify <slug> --static` once its `TODO` text is replaced and `cstudy verify <slug>` (D1, D3, D9, D10) on Go 1.27.3 (the oldest release of the Go 1.25 minimum is not yet observed).
- [ ] Step 1, Go, pilot: the build-graph runner on goroutines.
- [x] Step 2, Python and TypeScript, tooling: fixtures 9035 and 9036 pass, and a project scaffolded by `cstudy new --virtual-clock` passes `cstudy verify <slug>` with `clock 10/10`.
- [ ] Step 2, Python and TypeScript, pilot: the event pipeline.
- [x] Step 3, stress in projects, tooling: fixtures 9037 to 9042 pass in all six languages, and every combination `cstudy new --stress` supports (all six languages; with `--virtual-clock` for Go, Python, TypeScript, Kotlin and Rust; TypeScript only with the clock) passes `cstudy verify <slug>` with its broken overlay caught.
- [ ] Step 3, stress cases and broken overlays in projects, pilot: the message log.
- [x] Step 4, Kotlin coroutines, tooling: spike K7, fixtures 9043 and 9044 pass, and a scaffolded clock project passes `cstudy verify <slug>` with `clock 10/10`.
- [ ] Step 4, Kotlin coroutines, pilot: the coroutine service.
- [x] Step 5, Rust async on tokio, tooling: spike K8, fixtures 9045 and 9046 pass, and a scaffolded clock project passes `cstudy verify <slug>` with `clock 10/10`.
- [ ] Step 5, Rust async on tokio, pilot: the async component.

The pilots are written with the next project problems.

## Phase 11: Editor code intelligence

**Scope.** [ADR 0018](decisions/0018-editor-code-intelligence.md) and its spec amendments ([web-ui](specs/web-ui.md#code-intelligence-sessions), [cli](specs/cli.md#cstudy-doctor), [installation-and-workspaces](specs/installation-and-workspaces.md#layout), [architecture](architecture.md#web-adapter)): the `code_intelligence` and `autocomplete` preferences and the Settings view; Alt-Shift-click for a second cursor; the server catalog, the `code intelligence` doctor rows and `.cs/lsp/` installed by `cstudy doctor --fix`; the WebSocket session route on wsproto with its security rules and the broker; and, in the page's editor, live diagnostics, hover, go to definition with read-only library tabs, and, behind `autocomplete`, completion and signature help, which also governs the editor's own completion. One step per ADR phase and per release (owner's order, 2026-11-03), each with its slow tests against the real servers: 1 Python (basedpyright) and TypeScript (typescript-language-server), 2 Java on JDK 25 or 26 and Kotlin, with Kotlin starting from a spike of the alpha Kotlin LSP (if the spike fails, Java ships alone), 3 Go and Rust with pull diagnostics and documentation links that open library tabs. A server that is not a Node program keeps the hidden directories (`.cs/build/`, `.cs/cases/`, `.cs/runs/` and the content root) from itself in its own way.

**Exit criteria.** A step ends when its languages pass the slow real-server tests, every browser test passes in Playwright's Chromium, Firefox and WebKit against the fake server, the bundle meets NFR-12 and the code-intelligence chunk its own budget, and a manual run in the page shows an error as you type, a hover's documentation, a definition in the standard library and, with `autocomplete` on, a completion with its documentation.

- [x] The ADR is accepted and the specs amended before any implementation starts.
- [x] Step 1, Python and TypeScript, tooling: the `code_intelligence` and `autocomplete` preferences and their Settings checkboxes; Alt-Shift-click for a second cursor; the server catalog, the `code intelligence` doctor rows and `cstudy doctor --fix` installing basedpyright and typescript-language-server into `.cs/lsp/`; the WebSocket session route on wsproto and its broker, with `.cs/build/`, `.cs/cases/`, `.cs/runs/` and the content root hidden from the servers; in the page, live diagnostics, hover, go to definition with read-only library tabs, and completion and signature help behind `autocomplete`, which also governs the editor's own completion.
- [x] Step 1, Python and TypeScript, guide: [Code intelligence and autocomplete](guides/web-ui.md#code-intelligence-and-autocomplete) and the README feature list.
- [ ] Step 1, Python and TypeScript, release: the screenshots and animated GIFs, made from the released build, and the website message.
- [x] Step 2, Java: Eclipse JDT LS on JDK 25 or 26, after a spike on `jvm/` and a project folder (v0.29.0).
- [ ] Step 2, Kotlin: the open-source servers failed on Kotlin 2.4, so JetBrains' Kotlin LSP, behind a license you accept in `cstudy doctor --fix` (owner, 2026-11-08). In progress.
- [x] Step 3, Go and Rust, with pull diagnostics and documentation links that open library sources (v0.30.0).

## Phase 12: Service projects

**Status.** In progress: the tooling is built through P13, measured on macOS with Docker Desktop and on Linux with Docker Engine, and `0277` is its first problem, with `0278` its Python version, `0305` and `0306` its Java and Kotlin versions, `0310` its Go version, and `0279` and `0281` follow on mock servers alone. It runs after or around the releases of Phase 11, unless the owner reorders it.

**Scope.** [ADR 0019](decisions/0019-service-projects.md) and [its spec](specs/service-projects.md): project problems that always run in a Docker sandbox, with their own dependencies, standard lifecycle commands, one Python mock server, optional backing services, grading over HTTP, and a list of what each problem depends on. Existing problems stay native and need no Docker. One step per ADR phase, each with its docs and a website message at release: P1 the spike; P2 the environment allowlist, for all problems; P3 the sandbox runtime; P4 lifecycle commands, TypeScript and Python templates, install and lock rules; P5 the mock server and `cstudy dev`; P6 the HTTP grader with `verify` and CI; P7 the first problem in TypeScript; P8 its Python version; P9 code intelligence in the container and the Web UI; P10 data-driven problems; P11 mock server extensions and multi-step cases, with project-size security and AI problems; P12 Kotlin and Java; P13 Go; P14 Rust (maybe, decided when reached).

**Exit criteria.** A step ends when its [checks](specs/service-projects.md#checks) pass and, for a problem, `cstudy verify <slug> --require-ready` exits 0 and a manual run through all its levels works, from `cstudy start` to `cstudy done`.

- [x] P1: the spike, passed with changes on macOS; the sandbox is [measured on Linux](specs/service-projects.md#on-linux), with SELinux and rootless Docker unproven.
- [x] P2: the environment allowlist, for every problem ([Process environment](specs/runners.md#process-environment)).
- [x] P3 to P6: tooling: the sandbox, the lifecycle commands, the mock server, `cstudy dev` and the HTTP grader, with `verify` and a CI job on a real engine. P9 added `cstudy test --events` and `cstudy dev --events`, and the leftovers added `--no-run`, `--debug`, `--reset-data` and `--exec`.
- [x] P7: the first problem in TypeScript, `0277-coworking-availability-typescript`.
- [x] P8: the first problem in Python, `0278-coworking-availability-python`, graded by the same cases and mock servers as `0277`. The catalog then had 294 entries.
- [x] P9: code intelligence and Web UI. Built: TypeScript and Python [language servers](specs/service-projects.md#language-servers) in a sidecar, a calm state while Docker cannot run them, and on the page Run tests, Submit and Cancel, a dev stack panel with its scenario picker, the dependency list and Docker's states ([Web UI](specs/service-projects.md#web-ui)). The leftovers are built too: your own IDE's generated files (R29), a `devcontainer.json` that `cstudy dev` writes, and the dev flags of P3 to P6.
- [x] P10: data-driven problems. Built: [backing services](specs/service-projects.md#backing-services), with a Postgres and Redis fixture, `grade_setup` on them, Moto measured, and [grader reach](specs/service-projects.md#grader-reach) for PP3's identity provider. [Parallel cases](specs/service-projects.md#parallel-cases) are built too. Still planned: D7 for them, and contract tables (R9). The data-driven problems are PP5 to PP10 below, and all six are built.
- [x] P11: mock server extensions, multi-step cases, project-size security and AI problems. Built: [multi-step cases](specs/service-projects.md#multi-step-cases) with flows, cookie jars and captures, the app output check, log assertions on form fields and headers, and the mock server's [pass-through](specs/service-projects.md#pass-through) with token tampering, which reach P10's services through `grader_reach`. R33 is done: SSE streaming with drops and stalls, matching on request bodies, log assertions on JSON bodies, run-time values and an example mock LLM provider, with a [first-byte check](specs/service-projects.md#hidden-http-case), `first_byte_ms_max`, added so that a case can tell a stream from an answer held back until it is whole. PP3 is built as `0280`, and the AI and security problems as PP11, PP12, PP13 and PP15 below; PP14 is built as `0307`, below.
- [x] Engine gaps closed after PP7: a binary request body (`body_base64`), a sleep step, pausing, stopping and starting one backing service mid-case, and `restart: "app"`, which keeps the app's data between cases. `0284` now restarts with it. The other [known limits](specs/service-projects.md#known-limits) still hold.
- [x] P12: Kotlin and Java. Built: one Gradle image with JDK 25 for both, Gradle's user home in the project's install cache with every build after `install` offline, Gradle's verification file as the lock, the `project-java-service` and `project-kotlin-service` templates, a Java fixture on a real engine, and `0305-coworking-availability-java` and `0306-coworking-availability-kotlin`, graded by the same cases and mock servers as `0277` ([spec](specs/service-projects.md#templates-per-language)).
- [x] P13: Go. Built: `golang:1.27.3`, the Go cstudy's Go runner selects, Go's module cache and build cache in the project's install cache with every build after `install` at `GOPROXY=off` and `-mod=readonly`, so the modules are cached rather than vendored, `go.sum` as the lock, the `project-go-service` template, a Go fixture on a real engine, and `0310-coworking-availability-go`, graded by the same cases and mock servers as `0277` ([spec](specs/service-projects.md#templates-per-language)).
- [ ] P14: Rust (maybe), the next Phase 12 step.

## Phase 13: Catalog labels and new catalogs

**Status.** Steps 1 and 2 are built; step 3 is planned, not started. Step 3's project-size problems need Phase 12.

**Scope.** [ADR 0020](decisions/0020-catalog-labels.md): `domains`, `job_roles` and `scope` on problems and items, in closed lists; a one-pass backfill of the 270 existing entries; filters in `cstudy list`, `cstudy next` and the Problems view; then a first wave of function-size security and AI/LLM problems in Python and TypeScript.

**Exit criteria.** Every catalog entry passes the new static check, the filters give the same rows in the CLI and the page, and each new problem passes `cstudy verify <slug> --require-ready`.

- [x] Step 1: labels, backfill and filters: the vocabularies and schemas, S24, the backfill of the 270 entries, `--domain`, `--role` and `--scope` in `cstudy list` and `cstudy next`, and the web API parameters, with the Problems view's filters and Scope column.
- [x] Step 2: the first wave of function-size problems: seven in Python and TypeScript, `0255` to `0261`, with the language rule that lets the security, identity and AI/LLM domains list a subset. The catalog then had 277 entries.
- [x] TypeScript backend problems on today's engine: `0262` and `0263`, two small services to extend, then `0264` to `0271`, seven JavaScript traps on the debugging track and one asynchronous bug as a project on the virtual clock. The catalog then had 287 entries.
- [x] Backend reliability on the same engine: `0272` to `0276`, five TypeScript projects on an idempotent at-least-once consumer, a transactional outbox, retries on the virtual clock, optimistic locking, and reviewing an AI extraction, where the model proposes, code validates and a person decides. The catalog then had 292 entries.
- [x] Memory and retrieval practice: `0293` to `0303`, eleven function-size AI/LLM problems in Python and TypeScript, from memory stores and context packing to cosine top k, chunking and retrieval metrics. The catalog then had 318 entries.
- [x] Search box practice: `0304`, a search box with keyboard navigation, matching, stale responses and selection, in all six languages, as a plain class on an explicit clock. A browser-graded version waits for Phase 16. The catalog then had 319 entries.
- [x] P12 problems and two DSA additions: `0305` and `0306`, the Java and Kotlin versions of `0277`, `0307`, the built PP14, and `0308` and `0309`, two DSA problems (all grid paths on backtracking, and finding every missing and duplicate number, with a cyclic-sort optimum) that take the next free ids outside the stream plan, listed under [later DSA additions](specs/catalog.md#later-dsa-additions). The catalog then had 324 entries.
- [x] P13 problem and six more: `0310`, the Go version of `0277`, then `0311`, a tamper-evident ledger in four levels on hash chaining (Python, TypeScript, Java, Kotlin and Go); `0312`, a Python service project that loads a daily purchase file into Postgres once and asks a flaky bonus partner for points; `0313`, `0314` and `0316`, three four-level problems in all six languages on an org chart, referral counts and water poured on terrain; and `0315`, a Python project that checks a model's spans and adds a regex safety net before redacting text. The catalog then had 331 entries.
- [x] Knowledge representation (owner, 2026-11-11): five four-level problems: `0317` a taxonomy with several parents per concept, as in SKOS (all six languages); `0318` an ontology reasoner set against a closed-world validator, to show open-world inference beside SHACL-style validation; `0319` a triple store with pattern queries, `+` property paths, provenance and as-of answers (all six languages); `0320` entity resolution, from blocking and string similarity to clusters, a canonical record and B-cubed scores; `0321` a GraphRAG context builder that fits a neighbourhood into a token budget and cites the path behind each fact. `0318`, `0320` and `0321` are in Python and TypeScript. A guides path on the same topic follows them. All five are built: the catalog then had 336 entries.
- [x] Content-addressed storage (owner, 2026-11-11), `0322`, in four levels and all six languages, with a small SHA-256 helper in the Rust starter: content stored under its SHA-256 address and read back verified; folder snapshots as tree objects whose unchanged subtrees are shared and skipped when diffing; fixed-size chunking set against content-defined chunking on a rolling hash, with the dedup ratio; and named refs with mark-and-sweep garbage collection. It is the last step of the hashing guides path, after `0311`. Not the same as `0303`, which is compare-and-swap on versions. It is built: the catalog then had 337 entries.
- [x] AI engineering (owner, 2026-11-11): `0323` a loop controller with iteration, no-progress, token and time brakes and a completion check; `0324` a tool permission gate that instructions inside tool output can never change; `0325` context compaction with a stable cacheable prefix; `0326` an exact and semantic response cache with routing by query class and cost accounting; `0327` an eval release gate from assertions, judge scores and golden-set regressions; `0328` a guard that proves model-written SQL is a read-only query on allowed tables with a row limit; `0329` a plan-and-execute runner over a task graph with retries, replanning and budgets; `0330` corrective retrieval that grades what it found before trusting it; `0331` an agent trace analyzer. All in Python and TypeScript. All nine are built: the catalog then had 346 entries.
- [x] Data engineering (owner, 2026-11-12), all six languages: `0332` stream windows with event time, watermarks and late data; `0333` applying a change-data-capture log; `0334` a pipeline scheduler with partitions, idempotent reruns and backfills; `0335` a type 2 slowly changing dimension; `0336` a data quality gate; `0337` a table format with snapshots, time travel and optimistic commits; `0338` column-level lineage with impact analysis. All seven are built: the catalog then had 353 entries.
- [x] `0339`, an architecture checker that enforces layer and dependency rules on an import graph (owner, 2026-11-12), all six languages. It is built: the catalog then had 354 entries.
- [x] Infrastructure as code, as concepts (owner, 2026-11-12), all six languages: `0340` a plan engine that diffs desired and actual state and orders create, update, replace and delete; `0341` drift detection and import; `0342` idempotent converge with changed and ok results, check mode and handlers; `0343` layered values rendered into templates with schema validation; `0344` policy checks on deployment manifests. Problems on the real tools wait for [Phase 17](#phase-17-infrastructure-tools-in-the-sandbox). All five are built: the catalog then had 359 entries.
- [x] DSA on-ramps: `0345` to `0348`, four easy problems in all six languages, each a first step to a harder problem of its pattern: flood fill before counting islands, whether a path exists before counting connected components, a window of fixed width before windows that grow and shrink, and the kth largest of a stream before the kth largest element. They take the next free ids outside the stream plan, listed under [later DSA additions](specs/catalog.md#later-dsa-additions). The catalog then had 363 entries.
- [x] Guides paths after the hashing pilot: Getting started (the terminal, package managers, one "learn the language first" page per language, then a first problem), AI engineering, and Data engineering. Each guide is checked against primary sources and reviewed independently before it merges. All three are built.
- [x] Guides paths on the classic algorithm patterns: two pointers and sliding windows, binary search, graphs, trees and heaps, stacks, queues and tries, recursion and dynamic programming, and greedy choices and intervals. Each guide is checked against primary sources, reviewed independently, and checked for spoilers against every problem it links; the DSA on-ramps open the sections of their guides. All seven are built: with them there were 11 paths and 73 guides.
- [x] Tracing agent runs, a twelfth guide on the AI engineering path, after harness engineering: how a trace records an agent run as a tree of spans, and how to read it to roll up tokens and cost, find repeated tool calls and retry loops, and locate where a failure started. It is checked against primary sources and reviewed independently, and `0331` and harness engineering link it. It is built: the path then had 39 steps, and there were 11 paths and 74 guides.
- [x] Guides paths on testing, networking and security: "Testing", from your first assertion to mutation and contract tests, with 7 guides in 16 steps; "Networking", from packets to DNS, reliable transport, HTTP and retries, with 6 guides in 12 steps; and "Security", from trust boundaries to certificate chains and threat models, with 7 guides in 23 steps. Each guide is checked against primary sources and reviewed independently. All three are built: with them there were 14 paths and 94 guides.
- [x] Guides paths on machine learning, operating systems and distributed systems: "Machine learning fundamentals", from your first model to honest evaluation, with 7 guides in 12 steps; "Operating systems", from processes and scheduling to virtual memory and deadlock, with 6 guides in 16 steps; and "Distributed systems", from partial failure to consensus, with 8 guides in 17 steps. Each guide is checked against primary sources and reviewed independently. All three are built: with them there were 17 paths and 115 guides.
- [x] A guides path on database internals: "Database internals", from pages and B-trees to transactions and query plans, with 7 guides in 15 steps. Each guide is checked against primary sources and reviewed independently. It is built: with it there were 18 paths and 122 guides.
- [x] Guides paths on knowledge representation and on infrastructure as code: "Infrastructure as code", from desired state to plans, drift and policy checks, with 5 guides in 11 steps; and "Knowledge representation", from taxonomies to triples, reasoning and entity resolution, with 5 guides in 11 steps. Each guide is checked against primary sources and reviewed independently. Both are built: with them there were 20 paths and 132 guides.
- [x] Security, `0349` to `0351`, in Python and TypeScript: encoding output for the context it lands in, evaluating a CORS policy, and validating a certificate chain. All three are built: the catalog then had 366 entries.
- [x] Machine learning, `0352` and `0353`, in Python and TypeScript: classification metrics from confusion counts to ROC-AUC, and linear and logistic regression trained by gradient descent, with cross-validation and early stopping. Both are built: the catalog then had 368 entries.
- [x] Testing, `0354` and `0355`, all six languages: a library of test doubles, and a property-based test runner with shrinking and stateful tests. Both are built: the catalog then had 370 entries.
- [x] Networking, `0356` to `0358`, all six languages: an HTTP/1.1 request parser, a DNS resolver that follows referrals and caches answers, and reliable transport with retransmission, a sliding window and congestion control. All three are built: the catalog then had 373 entries.
- [x] Operating systems, `0359` and `0360`, all six languages: a CPU scheduler and virtual memory with a TLB and page replacement, both simulated. Both are built: the catalog then had 375 entries.
- [x] DSA fundamentals, `0361` to `0363`, all six languages: a sorting workbench in four levels, a practical problem, and substring search and the first bad commit, listed under [later DSA additions](specs/catalog.md#later-dsa-additions). All three are built: the catalog then had 378 entries.
- [x] Languages and editors, `0364` to `0366`, all six languages: a tiny interpreter, a line diff with a three-way merge, and an editor with undo and redo. All three are built: the catalog then had 381 entries.
- [x] Database internals, `0367` and `0368`, all six languages: a B+ tree index, and multiversion storage with snapshot isolation. Both are built: the catalog then had 383 entries.
- [x] Distributed systems, `0369` to `0372`, all six languages: logical clocks, a consistent hash ring, CRDT replicas and a Raft simulation. All four are built: the catalog then had 387 entries.
- [x] Platform, `0373` and `0374`, all six languages: a SemVer resolver, and alerts on an SLO's error budget burn rate. Both are built: the catalog then had 389 entries.
- [x] More DSA on-ramps: `0375` to `0380`, six problems in all six languages, each a first step in its pattern: lamp patterns before subsets, counting words by prefix before a whole trie, village paths before counting connected components, a rebate from the next cheaper item before daily temperatures, the cheapest route across a grid as a first two-dimensional table, and checking a task order before course schedule. They are listed under [later DSA additions](specs/catalog.md#later-dsa-additions). The catalog then had 395 entries.
- [x] Internals, `0381` to `0383`, all six languages: a regex engine by Thompson's construction, a query planner that estimates rows and orders joins by dynamic programming over subsets, and a memory allocator with boundary tags, placement policies and buddies. All three are built: the catalog then had 398 entries.
- [x] AI engineering, `0384` and `0385`, in Python and TypeScript: agent job workers, with leases, progress resumed from a shared store, a worker count set by the backlog and a gateway in front of the tools; and a grounded memory store whose claims cite receipts of their sources, go stale when a source changes, and are re-verified or contradicted. Both are built: the catalog then had 400 entries.
- [ ] Step 3: later waves: project-size problems need Phase 12, and system-size ones need later design.

### Planned project problems

The owner accepted this list on 2026-11-08. Each is original and new; none replaces a problem in the catalog. Each starts in TypeScript, with a Python version after it, and Java, Kotlin and Go versions follow for the strongest. They are grouped by the Phase 12 step that makes them possible. Domains and roles use the closed lists of [ADR 0020](decisions/0020-catalog-labels.md); PP10, PP12 and PP13 are the hardest of the hard.

**With mock servers only (PP1, PP2 and PP4 built; PP3 moved):**

| ID | Project | Domains · roles | What it teaches | Difficulty |
|----|---------|-----------------|-----------------|------------|
| PP1 | Coworking availability in Python (P8) | backend · backend | `0277` in a second language | hard |
| PP2 | Payment webhook receiver | fintech, security · backend, security-engineer | HMAC signatures, replay windows, idempotency, events out of order, a provider's retries | medium |
| PP3 | OAuth client with PKCE against an identity provider (`0280`, on Keycloak) | identity, security · backend, security-engineer | The code flow with PKCE, token refresh, rotated signing keys, clock skew, revoked tokens; the whole flow that `0255` and `0256` cover in parts | hard |
| PP4 | SSRF-safe webhook dispatcher | security · security-engineer, backend | User-supplied URLs: blocking internal addresses, following redirects safely, timeouts, signing | hard |

PP3 waited for P10's backing services and grader reach and for P11's multi-step cases, because a mock server does not sign tokens per request ([ADR 0019](decisions/0019-service-projects.md), R34). It is built as `0280`, with Keycloak as the identity provider behind a mock server's pass-through.

**With backing services (P10: Postgres, Redis or Valkey, AWS services through Moto):**

| ID | Project | Domains · roles | What it teaches | Difficulty |
|----|---------|-----------------|-----------------|------------|
| PP5 | Inventory reservations | backend · backend | What a real database adds to `0275`: `SELECT … FOR UPDATE`, isolation levels, constraints, and migrations you design | hard |
| PP6 | A job queue on Postgres | backend · backend, platform | Building the queue itself, where `0272` consumes one: claiming with `SKIP LOCKED`, timeouts for stuck work, retries with backoff, a dead-letter table | hard |
| PP7 | File ingestion through S3 and SQS | backend · backend, platform | Uploads to S3, events on SQS, validating large CSV files into Postgres, poison messages | hard |
| PP8 | Multi-tenant API | backend, security · backend, security-engineer | Tenant isolation with row-level security, graded by IDOR attack requests | hard |
| PP9 | Rate limiter and cache on Redis | backend · backend, platform | Sliding-window limits, cache-aside with invalidation, hot keys, Redis going down | medium |
| PP10 | Event-sourced ledger | fintech, backend · backend | Append-only events, projections, rebuilding them, snapshots | hard |

**With mock server extensions (P11: streaming, LLM provider mocks):**

| ID | Project | Domains · roles | What it teaches | Difficulty |
|----|---------|-----------------|-----------------|------------|
| PP11 | LLM gateway | ai-llm, backend · backend, ai-engineer | Streaming over SSE, 429 and backoff, falling back to a second provider, token budgets and cost, building on `0259` | hard |
| PP12 | RAG service with citations | ai-llm · ai-engineer | Chunking, a mock embeddings API, vector search in Postgres, answers graded on retrieval and grounding | hard |
| PP13 | Tool-calling agent loop | ai-llm, security · ai-engineer, security-engineer | A tool allowlist, prompt injection hidden in tool output, step and cost budgets, failing safely | hard |
| PP14 | Fix the vulnerable service | security · security-engineer | A working app with broken authentication, IDOR, mass assignment and path traversal, graded by attack cases that must fail and normal cases that must keep passing | hard |
| PP15 | Secure file upload | security, backend · backend, security-engineer | Size limits, content sniffing, path traversal, a mock malware-scan vendor that fails | medium |

Suggested order: PP1 to PP15 are built. P9, code intelligence and the Web UI, is built. P12 brought the service problems to the JVM, Kotlin and Java, and P13 to Go. Next is P14, Rust (maybe), then Phase 16, the frontend problems. D7 and contract tables (R9) come in when a problem needs them.

- [x] PP1: `0278-coworking-availability-python` (P8).
- [x] PP2: `0279-payment-webhook-receiver-typescript`.
- [x] PP4: `0281-ssrf-safe-webhook-dispatcher-typescript`. The catalog now has 296 entries.
- [x] PP3: `0280-oauth-pkce-client-typescript`, with Keycloak as the identity provider.
- [x] PP5: `0282-inventory-reservations-typescript`, on Postgres with node-pg-migrate. The catalog now has 298 entries.
- [x] PP6: `0283-postgres-job-queue-typescript`, on Postgres.
- [x] PP7: `0284-csv-upload-ingestion-typescript`, on Postgres and Moto. It is the first problem on Moto, with S3 and SQS.
- [x] PP8: `0286-multi-tenant-api-typescript`, on Postgres with row-level security.
- [x] PP9: `0285-price-cache-rate-limits-typescript`, on Valkey (BSD-licensed and Redis-compatible), not Redis, behind a mock pricing vendor.
- [x] PP10: `0287-event-sourced-ledger-typescript`, on Postgres. The catalog now has 303 entries.
- [x] PP15: `0289-secure-file-upload-typescript`, behind a mock malware scanner.
- [x] PP11: `0290-llm-gateway-typescript`, on two mock LLM providers, with a hidden case that times the first byte of a slow stream.
- [x] PP12: `0291-rag-citations-typescript`, on pgvector with mock embeddings and chat APIs.
- [x] PP13: `0292-tool-calling-agent-loop-typescript`, on a mock model and mock tool APIs. The catalog now has 307 entries.
- [x] PP14: `0307-fix-the-flaws-typescript`, in four levels: notes that belong to someone else, names and fields taken from the request, text that becomes a query, and logs and errors. The learner receives a working service with the flaws described as review findings and closes them, graded by attack cases that must fail and normal cases that must keep passing.

## Phase 14: AI-reviewed problems

**Status.** Steps 1 and 2 are part of the AI preview of [v1.0.0](#v100), milestones v0.59 to v0.61, as a wider design that adds the assistant and problem sessions; the 16 items are rubric-checked problems by then. Steps 3 and 4 come after 1.1.

**Scope.** [ADR 0021](decisions/0021-ai-reviewed-problems.md): an opt-in class of problems reviewed by a live LLM with your own key. It needs the environment allowlist of Phase 12's P2, which is built.

- [ ] Step 1: provider port and keys.
- [ ] Step 2: written answers on existing items.
- [ ] Step 3: simulated interview.
- [ ] Step 4: whiteboard, after its spike.

## Phase 15: Problem sets

**Status.** Built; it does not wait for Phases 12 and 14.

**Scope.** [ADR 0023](decisions/0023-problem-sets.md): named, ordered lists of problems and items in `sets.yaml`, with `cstudy set`, `--set` on `cstudy list` and `cstudy next`, a Set filter, an add-to-set control and a Sets view on the page. Sets shipped in the catalog, a language per set and due dates are later options.

**Exit criteria.** A problem can be in two sets, a set's rows and order match between the CLI and the page, `cstudy reset` keeps sets with or without `--files`, and a hand-edited invalid file gives a clear error and is never overwritten.

- [x] `sets.yaml`, its store and its validation.
- [x] `cstudy set`, and `--set` on `cstudy list` and `cstudy next`.
- [x] The web API under the page's write rules.
- [x] The Set filter, the add-to-set control and the Sets view.

## Phase 16: Frontend problems

**Status.** Planned for [v1.0.0](#v100), milestone v0.58; not started.

**Scope.** Problems where you fix or build a real UI component, such as a search box with keyboard navigation, graded by driving the page in a headless browser inside the sandbox: pressing keys, reading what is highlighted, and checking what the page asked the server. It needs a browser image in the sandbox, a grader that drives it, and a decision on frameworks (React first). Until then, the logic of such problems is taught as state machines driven by events, such as the autocomplete problem below, which can later move here.

- [ ] An ADR and a spike: a browser in the sandbox (size, memory, offline), how cases drive it, and how a learner runs it with `cstudy dev`.
- [ ] The grader and the first problem, a search box with keyboard navigation and server matching.

## Phase 17: Infrastructure tools in the sandbox

**Status.** Planned, not started (owner, 2026-11-12).

**Scope.** Problems where you write real infrastructure code, such as a Terraform module, a Helm chart or an Ansible playbook, graded by running the real tool in the sandbox with no network: `plan` against a local or mock provider, chart rendering and linting, and a playbook run against a throwaway container, with its idempotence checked by a second run. The concept problems `0340` to `0344` teach the ideas first, on today's engine.

- [ ] An ADR and a spike: tool images and their size, offline provider and plugin mirrors, licensing of each tool, how cases check a plan or a render, and how a learner runs it with `cstudy dev`.
- [ ] The first problem on each tool.

