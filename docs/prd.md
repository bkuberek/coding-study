# Product Requirements: coding-study

A local, IDE-first interview-prep system for senior and staff engineer loops. You solve problems in your own editor, and a CLI (`cstudy`) does everything a practice website would: it picks the next problem, scaffolds a stub, runs tests, reveals solutions, analyzes performance and tracks progress.

| Field | Value |
|-------|-------|
| Status | Implemented through Phase 7; open validation items in the [roadmap](roadmap.md#status) |
| Users | One engineer per installation, practicing on their own machine |
| Platform | macOS, local only |
| Languages practiced | Python, TypeScript, Java, Kotlin, Go and Rust ([ADR 0012](decisions/0012-go-and-rust.md)); a project problem is in one language ([ADR 0014](decisions/0014-project-problems.md)) |
| Related | [Architecture](architecture.md), [Roadmap](roadmap.md), [Specs](README.md#specs) |

## 1. Executive summary

**Problem.** Browser-based practice sites force a foreign editor, give no control over content, cover DSA only, and treat each language as a separate silo. Senior and staff loops also test practical multi-level coding, object-oriented design, concurrency, system design, code review and behavioral skills, which those sites do not cover.

**Solution.** A CLI that ships with a catalog of original, data-defined problems. You write code in your editor, such as LazyVim or IntelliJ, inside real per-language projects in a workspace of your own (LSP and debugger work). The CLI executes that code against language-neutral test data, compares behavior, measures performance against a ladder of reference approaches, and schedules reviews with spaced repetition weighted toward weak patterns.

**Success criteria.**

| KPI | Target |
|-----|--------|
| Edit-to-feedback loop (`cstudy test`, warm) | p50 at or under 1.0 s for Python and TypeScript, 3 s for Java, 5 s for Kotlin |
| DSA content | 185 `ready` problems by end of Phase 3, each passing `cstudy verify` in all 4 languages |
| Content correctness | 0 reference solutions failing `cstudy verify` on the main branch |
| Practice cadence | At least 5 finished attempts per week, measured by `cstudy stats` |
| Interview readiness | Median solve time for medium problems on review attempts at or under 25 min |

## 2. User experience and functionality

### Persona

A senior or staff engineer preparing for interviews, practicing alone. Works in a terminal editor such as Neovim (LazyVim) inside a terminal multiplexer, or in IntelliJ for JVM code, and prefers keyboard-driven tools.

### Core loop

```text
cstudy next  ->  cstudy start <slug> --lang kotlin  ->  edit in editor  ->  cstudy test --watch
         ->  cstudy bench (optional)  ->  cstudy done --rating ok  ->  cstudy solution (optional)
```

### User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|----|-------|---------------------|
| US-1 | As the user, I want `cstudy next` to choose what to practice, so that I spend time on due reviews and weak patterns instead of browsing. | Due reviews come first; otherwise a new problem from the weakest pattern; the reason is printed; selection is deterministic for the same database state. |
| US-2 | As the user, I want `cstudy start` to create an idiomatic stub in a real project for my language, so that my editor's LSP, formatter and debugger work. | Stub lands at the documented path; compiles or imports unchanged; the statement opens in `$EDITOR`. |
| US-3 | As the user, I want `cstudy test` to run my code against all cases and show per-case results with diffs, so that I can iterate quickly. | Each case reports pass, fail, error, timeout or TLE; failures show input, expected and actual; exit code reflects the result. |
| US-4 | As the user, I want correctness to be judged by behavior, so that any valid solution passes regardless of how it is written. | User code is executed and its output compared with expected values through the problem's comparator; no textual comparison with reference code exists anywhere. |
| US-5 | As the user, I want an optional time limit, so that brute force fails large cases like on LeetCode when I choose. | Off by default; enabled by flag or config; precedence flag over config over problem default. |
| US-6 | As the user, I want `cstudy bench` to place my solution on a complexity ladder of reference approaches, so that I know whether it is optimal. | Shows per-size timings and memory for my code and every reference approach in the same runtime, an empirical growth class, a verdict with confidence, and comparison to my own past runs. |
| US-7 | As the user, I want `cstudy solution` to show reference code with a full explanation, so that I learn every approach and its trade-offs. | Shows the chosen approach's code for the language plus intuition, algorithm, correctness, complexity, trade-offs, pitfalls and language notes. |
| US-8 | As the user, I want `cstudy done` to log the attempt and schedule the next review, so that I retain what I learned. | Attempt stored with time, result, rating, hints and solution reveals; next due date computed by the specified algorithm. |
| US-9 | As the user, I want to author my own problems with `cstudy new` and `cstudy verify`, so that the catalog grows with what I encounter. | Scaffold from templates; JSON Schema validation; verify reports pass/fail and per-language coverage. |
| US-10 | As the user, I want non-autograded tracks (system design, code review, behavioral) in the same loop, so that all interview areas are tracked in one place. | Prompts, rubrics and reference material open through `cstudy start` and `cstudy solution`; attempts are logged and scheduled. |
| US-11 | As the user, I want timed practice, so that I rehearse interview pressure. | `--timer 25m` shows elapsed and remaining time; finishing over time caps the review grade. |
| US-12 | As the user, I want project problems: a folder of seeded files in one language that I extend level by level and test with that language's own tools, so that I practice building and changing a small codebase. | `cstudy start` seeds `projects/<slug>/`; `cstudy test` runs native tests generated from the visible cases plus my own; `cstudy submit` grades every case of the unlocked levels, hidden ones included, and opens the next level on a full pass; `cstudy done` grades by the levels finished. |

### Non-goals

- No web UI, browser editor, accounts, multi-user support or leaderboards.
- No textual or AST comparison of user code with reference code.
- No AI grading of code, designs or behavioral answers.
- No copying of LeetCode statements or test data ([ADR 0004](decisions/0004-original-problem-wording.md)).
- No languages beyond Python, TypeScript, Java and Kotlin in v1, except Go and Rust, which are added after v1 ([ADR 0012](decisions/0012-go-and-rust.md)).
- No Windows or Linux support commitment (macOS only; nothing deliberately prevents Linux).

## 3. AI system requirements

Not applicable. The product contains no AI features.

## 4. Requirements

### Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Correctness is behavioral: the CLI executes the user's code, captures its output and compares it with expected values using the problem's comparator (exact, unordered, unordered-nested, float, checker, ops). Any valid answer passes; multi-answer problems use a checker. Reference solutions are never compared with user code. |
| FR-2 | Tests are language-neutral data (`tests.json`); one runner per runtime executes any problem ([ADR 0001](decisions/0001-data-driven-tests.md)). A project problem's native visible tests are generated from that data, and its grade still comes from the data, judged by the core ([ADR 0014](decisions/0014-project-problems.md)). |
| FR-3 | Signatures are declared once in a type DSL and generated into idiomatic stubs for every language a problem lists, using the mapping in [problem-format](specs/problem-format.md#type-dsl). Every catalog problem lists all six languages unless a language cannot express it, it is on the concurrency or debugging track, or it is a project problem, which lists one language and starts from a seeded folder instead of a stub. |
| FR-4 | Every problem ships a full description (`problem.md`: statement, input, output, examples with explanations, constraints; optional follow-ups and progressive hints). |
| FR-5 | Every problem ships one or more reference approaches tagged with time and space complexity, and every approach has an explanation section in the mandated format. Missing items fail `cstudy verify`. |
| FR-6 | A problem may ship references in a subset of languages while in `draft`; `ready` problems require the optimal approach in every listed language. `cstudy verify` reports coverage per language. |
| FR-7 | `cstudy verify` validates `meta.yaml` and `tests.json` against JSON Schemas, runs every reference approach in every language against all cases, and optionally cross-checks against a brute-force oracle on randomized inputs. |
| FR-8 | Time limits are optional and off by default. Enablement precedence: CLI flag over user config. Value precedence: CLI flag over user config over the problem's `meta.yaml` suggestion over the built-in factor. A hang guard (default 10 s per case) always applies, independent of time limits. |
| FR-9 | `cstudy bench` measures the user's code and all reference approaches on the same generated inputs in the same runtime and reports time, memory, empirical growth class, a verdict with confidence, and history ([performance-analysis](specs/performance-analysis.md)). |
| FR-10 | Progress is stored in SQLite: attempts, test runs, schedule, bench runs ([progress-and-scheduling](specs/progress-and-scheduling.md)). |
| FR-11 | `cstudy next` selects due reviews first, then new problems from the weakest pattern, using the deterministic formula in the progress spec. |
| FR-12 | Content tracks: DSA, practical (progressive and project), low-level design, concurrency, system design, code review and debugging, behavioral (guidance only) ([content](specs/content.md)). |
| FR-13 | Users author problems with `cstudy new` templates and the workflow in [authoring](specs/authoring.md). |
| FR-14 | Reference solutions stay outside the workspace; nothing the user opens by default shows them. |
| FR-15 | Project problems: a problem may be a folder of seeded files in one language, solved level by level in `projects/<slug>/`. `cstudy test` runs its native tests as feedback; `cstudy submit` grades every case of the unlocked levels through the runner and opens the next level ([ADR 0014](decisions/0014-project-problems.md)). Python and TypeScript first; Java, Kotlin, Go and Rust are not yet supported. |

### Non-functional requirements

| ID | Requirement | Measure |
|----|-------------|---------|
| NFR-1 | Fast feedback | `cstudy test` warm p50: Python and TypeScript 1.0 s, Java 3 s, Kotlin 5 s, and, once their runners exist, Go 1.0 s and Rust 2 s, for at most 50 cases of an O(n log n) solution; for a Python or TypeScript project problem, `cstudy test` and `cstudy submit` each within 1.0 s. JVM cold start (first build after daemon stop) up to 60 s is accepted and printed as "warming Gradle daemon". |
| NFR-2 | Fast CLI | `cstudy list`, `cstudy next`, `cstudy stats` complete in at most 500 ms with 250 problems (index cache). |
| NFR-3 | Verify throughput | Full `cstudy verify` (no oracle, no ladder) over 200 problems in the 4 core languages in at most 10 min (Go and Rust are gated per batch with `cstudy verify --lang`, [ADR 0012](decisions/0012-go-and-rust.md)); `cstudy verify <slug>` in at most 30 s warm. |
| NFR-4 | Determinism | Same inputs, database and seed produce the same `cstudy next` choice, generated cases and oracle cases. |
| NFR-5 | Isolation | A crash, infinite loop or `System.exit` in user code never crashes the CLI; it is reported as a case or runner error. |
| NFR-6 | Offline | All commands work offline after the one-time toolchain setup. |
| NFR-7 | Editor integration | Each practice project of a workspace (`python/`, `typescript/`, `jvm/`) is a standard project (uv, pnpm, Gradle) that LazyVim LSPs and IntelliJ open without custom configuration. |
| NFR-8 | Architecture | Domain core has no imports of I/O, subprocess, SQLite or filesystem modules; enforced by an import contract test. |
| NFR-9 | Honest measurement | Performance verdicts always carry a confidence level and never claim more precision than the data supports. |

## 5. Technical overview

See [architecture](architecture.md) for components and data flows.

| Area | Decision |
|------|----------|
| CLI | Python 3.13 with uv ([ADR 0002](decisions/0002-python-uv-cli.md)) |
| Runners | Python (venv), TypeScript (Node 24 type stripping), JVM (one runner for Java and Kotlin, built with the Gradle wrapper, [ADR 0003](decisions/0003-gradle-wrapper-jvm.md)) |
| Storage | Content in files (YAML, JSON, Markdown); progress in SQLite `progress.db` |
| Integration | Subprocess plus JSON files between CLI and runners ([runners](specs/runners.md)) |
| Security and privacy | Local only; no network at runtime; content code (generators, checkers) is trusted repository code; user code runs as the user with a hang guard but no sandbox |

## 6. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Type mapping errors across 4 languages | Wrong stubs or false failures | Runner conformance suite covering every DSL type in every runtime; Phase 0 exit criterion |
| JVM latency (Gradle, Kotlin compiler) | Slow loop, lower use | Gradle daemon plus configuration cache, compile only the active problem, fresh JVM with cached classpath; persistent JVM is an open question |
| Content authoring cost (4 languages, several approaches, explanations) | Catalog grows slowly | Data-driven tests, `cstudy new` templates, oracle cross-check; `draft` status allows partial coverage |
| Measurement noise (GC, JIT, thermal throttling, background load) | Unstable verdicts | Warmup, repetitions, interleaved targets, medians with spread, confidence levels |
| Complexity misclassification (n versus n log n is not separable by slope) | Misleading "optimal" claims | Use ratio to the optimal reference at the largest size for that band; report confidence; document limits ([ADR 0005](decisions/0005-empirical-complexity-analysis.md)) |
| Memory metrics differ by runtime | Cross-language confusion | Compare memory only within one language against that language's references |
| Copyright | Takedown risk for the public repository | Original wording only ([ADR 0004](decisions/0004-original-problem-wording.md)) |
| The former CLI name `cs` collided with Coursier's `cs` binary | Shadowed command on JVM machines | Resolved: the command is `cstudy`; see open question Q1 |

## 7. Roadmap

Phases and exit criteria: [roadmap](roadmap.md).

## 8. Open questions

Each item has a recommended default that the specs already assume, or the decision that closed it. Changing either requires updating the referenced spec.

| ID | Question | Recommended default or decision |
|----|----------|---------------------------------|
| Q1 | Final CLI name: keep `cs` (collides with Coursier's `cs`) or rename? | **Decided**: `cstudy`, renamed from `cs` to avoid the Coursier collision, which shadowed the command on JVM and Scala machines. The repository and package keep the name `coding-study` / `coding_study`; there is no `cs` alias, and the `.cs/` workspace state directory is unchanged. |
| Q2 | Should `progress.db` be backed up in git? | Gitignored; `cstudy export` writes `progress-export.json`, which the user may commit, and `cstudy import` restores it into an empty database (Phase 7). |
| Q3 | Should `cstudy done` auto-commit the workspace file? | No; the user commits. Config key `done.auto_commit` reserved, default `false`. Adopted in Phase 1: `cstudy` never runs git on practice files; practice files and `.archive/` stay tracked (not ignored), so the user commits attempts when they choose. Since W1 ([ADR 0008](decisions/0008-installable-tool-and-separate-workspaces.md)) they live in a workspace outside this repository, versioned in the user's own repository; `cstudy init --git` only runs `git init`. |
| Q4 | Persistent JVM runner (compile server) to beat the Gradle path? | **Decided** ([ADR 0007](decisions/0007-no-persistent-jvm-runner.md)): no, not in v1. Phase 7 warm `cstudy test` p50 under background load: Java 1.36 to 2.23 s (target 3 s), Kotlin 1.44 to 1.85 s (target 5 s), Python 0.47 to 0.65 s and TypeScript 0.44 to 0.46 s (target 1.0 s). The Gradle step is most of the JVM time; revisit when a quiet-machine Java or Kotlin p50 exceeds two thirds of its target. |
| Q5 | Kotlin coroutine variants in the concurrency track autograded? | **Decided** ([ADR 0006](decisions/0006-concurrency-stress-testing.md)): no, threads only in v1. Kotlin runs the `threads` model (platform and virtual threads) through the shared JVM runner; coroutine designs are a required paragraph of `### Language notes`. A `suspend fun` adds a `Continuation` parameter, which breaks the JVM erasure property the one runner relies on. |
| Q6 | Concurrency stress-scenario schema | **Decided** ([ADR 0006](decisions/0006-concurrency-stress-testing.md), [problem-format](specs/problem-format.md#concurrent-problems)): `stress` cases with a single-threaded setup, worker groups running templated op scripts behind a start gate, an optional quiescent final sequence, and invariants (multisets, distinctness, bounds, counts, sums, per-source order, probe sections, checker) evaluated by the CLI. A case passes only if all N runs pass; broken references must fail in at least 9 of 10 runs. |
| Q7 | 64-bit integers beyond 2^53 in TypeScript | Forbidden in content (verify rejects); revisit with `bigint` only if a needed problem requires it. |
| Q8 | Should suboptimal bench verdicts shorten the review interval? | Yes, config `schedule.penalize_suboptimal = true`, only with confidence medium or high. |
| Q9 | Default scope of `cstudy next` | `["dsa"]`; other tracks by `--track` or config `next.tracks`. |
| Q10 | Should failing hidden cases reveal their input? | Yes (practice value over secrecy); passing hidden cases are collapsed to a count. |
| Q11 | Publish the repository publicly? | **Decided**: public, under the [MIT license](../LICENSE), which covers the code and the original problem content. Original wording ([ADR 0004](decisions/0004-original-problem-wording.md)) makes publication possible, and separate workspaces ([ADR 0008](decisions/0008-installable-tool-and-separate-workspaces.md)) keep solutions and progress out of the repository. |
| Q12 | Should `cstudy import` merge an export into a database that already holds progress (two machines, or a restore over newer practice)? | No: `cstudy import` needs an empty database and refuses otherwise, so a restore never mixes or overwrites rows. Merging needs rules for colliding ids and two schedules for one problem; revisit if practice on two machines becomes real. |
| Q13 | Should a workspace hold non-autograded items of its own (`tracks/`), as it holds its own `problems/`? | No for now: only `problems/` is overlaid ([installation-and-workspaces](specs/installation-and-workspaces.md#your-own-problems)); `cstudy new` scaffolds only problems, and items keep coming from the content. Revisit when someone wants to write their own system design or code review items. |
| Q14 | Should `cstudy init` write the workspace's own `config.toml` (per-workspace defaults such as `default_lang`)? | No for now: one user-level config file applies to every workspace ([cli](specs/cli.md#configuration)), so nothing personal is versioned with the workspace by default. |
