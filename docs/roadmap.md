# Roadmap

Each phase ends only when every exit criterion is observed. Phases run in order; content batches inside Phases 1 and 3 each pass the full verify gate before merging.

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
| 12 | Service projects (planned, not started) | `dev`, `start --yes`, `list --needs`, `verify` S19 to S23 and D11 |

## Status

Phases 0 to 7 are implemented: every command in the table above exists with its tests, and the catalog holds 213 `ready` problems and 16 `ready` items. Exit criteria with recorded evidence are ticked in the phase sections. These validation items are still open:

| Item | Phase | Needs |
|------|-------|-------|
| LazyVim shows language-server diagnostics in a fresh stub for each language, without extra configuration | 0 | A manual editor check |
| IntelliJ imports a workspace's `jvm/` as a Gradle project with both subprojects | 0 | A manual editor check |
| At least 10 attempts through `next`, `start`, `test`, `done` | 1 | Real practice |
| `cstudy verify --oracle --ladder --require-ready` exits 0 over the whole catalog | 2, 3 | Ladder band fixes in progress; the oracle check already passes everywhere |
| Bench verdicts for 5 problems with an O(n^2) brute force, and their stability over 5 runs | 2 | A recorded run on an idle machine |
| Full `cstudy verify` (no oracle, no ladder) within the NFR-3 time | 3 | A recorded timing |

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
- [ ] Step 2, Java and Kotlin: Java first on JDK 25 or 26 after a spike on `jvm/` and a project folder; Kotlin from a spike of the Kotlin LSP, and Java alone if it fails.
- [ ] Step 3, Go and Rust.

## Phase 12: Service projects

**Status.** Planned, not started. It runs after or around the releases of Phase 11, unless the owner reorders it.

**Scope.** [ADR 0019](decisions/0019-service-projects.md) and [its spec](specs/service-projects.md): project problems that always run in a Docker sandbox, with their own dependencies, standard lifecycle commands, one Python mock server, optional backing services, grading over HTTP, and a list of what each problem depends on. Existing problems stay native and need no Docker. One step per ADR phase, each with its docs and a website message at release: P1 the spike; P2 the environment allowlist, for all problems; P3 the sandbox runtime; P4 lifecycle commands, TypeScript and Python templates, install and lock rules; P5 the mock server and `cstudy dev`; P6 the HTTP grader with `verify` and CI; P7 the first problem in TypeScript; P8 its Python version; P9 code intelligence in the container and the Web UI; P10 data-driven problems; P11 mock server extensions and multi-step cases, with project-size security and AI problems; P12 Kotlin and Java; P13 Go; P14 Rust (maybe, decided when reached).

**Exit criteria.** A step ends when its [checks](specs/service-projects.md#checks) pass and, for a problem, `cstudy verify <slug> --require-ready` exits 0 and a manual run through all its levels works, from `cstudy start` to `cstudy done`.

- [ ] P1: the spike on macOS and Linux; if it fails, the owner decides before anything is built.
- [ ] P2: the environment allowlist.
- [ ] P3 to P6: tooling.
- [ ] P7: the first problem in TypeScript.
- [ ] P8: the first problem in Python.
- [ ] P9: code intelligence and Web UI.
- [ ] P10: data-driven problems.
- [ ] P11: mock server extensions, multi-step cases, project-size security and AI problems.
- [ ] P12 to P14: Kotlin and Java, Go, Rust (maybe).

## Phase 13: Catalog labels and new catalogs

**Status.** Steps 1 and 2 are built; step 3 is planned, not started. Step 3's project-size problems need Phase 12.

**Scope.** [ADR 0020](decisions/0020-catalog-labels.md): `domains`, `job_roles` and `scope` on problems and items, in closed lists; a one-pass backfill of the 270 existing entries; filters in `cstudy list`, `cstudy next` and the Problems view; then a first wave of function-size security and AI/LLM problems in Python and TypeScript.

**Exit criteria.** Every catalog entry passes the new static check, the filters give the same rows in the CLI and the page, and each new problem passes `cstudy verify <slug> --require-ready`.

- [x] Step 1: labels, backfill and filters: the vocabularies and schemas, S24, the backfill of the 270 entries, `--domain`, `--role` and `--scope` in `cstudy list` and `cstudy next`, and the web API parameters, with the Problems view's filters and Scope column.
- [x] Step 2: the first wave of function-size problems: seven in Python and TypeScript, `0255` to `0261`, with the language rule that lets the security, identity and AI/LLM domains list a subset. The catalog then had 277 entries.
- [x] TypeScript backend problems on today's engine: `0262` and `0263`, two small services to extend, then `0264` to `0271`, seven JavaScript traps on the debugging track and one asynchronous bug as a project on the virtual clock. The catalog then had 287 entries.
- [x] Backend reliability on the same engine: `0272` to `0276`, five TypeScript projects on an idempotent at-least-once consumer, a transactional outbox, retries on the virtual clock, optimistic locking, and reviewing an AI extraction, where the model proposes, code validates and a person decides. The catalog now has 292 entries.
- [ ] Step 3: later waves: project-size problems need Phase 12, and system-size ones need later design.

## Phase 14: AI-reviewed problems

**Status.** Planned for the future, not started, with no commitment beyond this order. It sits after Phases 12 and 13, unless the owner reorders it.

**Scope.** [ADR 0021](decisions/0021-ai-reviewed-problems.md): an opt-in class of problems reviewed by a live LLM with your own key. It needs the environment allowlist of Phase 12's P2.

- [ ] Step 1: provider port and keys.
- [ ] Step 2: written answers on existing items.
- [ ] Step 3: simulated interview.
- [ ] Step 4: whiteboard, after its spike.
