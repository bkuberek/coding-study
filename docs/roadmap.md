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
| 12 | Service projects | `dev`, `start --yes`, `list --needs`, `verify` S19 to S23 and D11 |

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
- [x] P13 problem: `0310`, the Go version of `0277`. The catalog then had 325 entries.
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

**Status.** Planned for the future, not started, with no commitment beyond this order. It sits after Phases 12 and 13, unless the owner reorders it.

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

**Status.** Planned, not started (owner, 2026-11-10).

**Scope.** Problems where you fix or build a real UI component, such as a search box with keyboard navigation, graded by driving the page in a headless browser inside the sandbox: pressing keys, reading what is highlighted, and checking what the page asked the server. It needs a browser image in the sandbox, a grader that drives it, and a decision on frameworks (React first). Until then, the logic of such problems is taught as state machines driven by events, such as the autocomplete problem below, which can later move here.

- [ ] An ADR and a spike: a browser in the sandbox (size, memory, offline), how cases drive it, and how a learner runs it with `cstudy dev`.
- [ ] The grader and the first problem, a search box with keyboard navigation and server matching.
