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
- [x] 8e, Go, `bank-project-go`: fixtures 9030 and 9031; NFR-1 1.5 s.
- [x] 8f, Rust, `bank-project-rust`: fixtures 9032 and 9033; NFR-1 2 s.
