# ADR 0006: Concurrency problems are stress-tested against invariants and proven by broken references

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Spec | [problem-format](../specs/problem-format.md#concurrent-problems), [runners](../specs/runners.md#concurrent-jobs) |
| Closes | PRD Q5, Q6 |

## Context

The concurrency track must autograde thread-safe classes in four languages with very different concurrency models: the JVM has true parallelism with platform and virtual threads; CPython 3.13 has threads under the GIL plus `asyncio`; Node has one event loop, and its `worker_threads` cannot share objects; Kotlin's coroutines need `kotlinx.coroutines` and compile `suspend` functions to a different JVM signature. Thread schedules are not reproducible, so one passing run says little, and a test that never produces an interleaving passes every implementation. Phase 5 requires that an unsynchronized reference fail its stress case in at least 9 of 10 runs and the correct reference pass 10 of 10.

## Decision

- A `concurrent` problem is a class kind with sequential `ops` cases plus `stress` cases. A stress case is a single-threaded setup, worker groups running op scripts released together by a start gate, an optional quiescent final sequence, and invariants.
- Two models: `threads` (Java, Kotlin, Python) and `async` (Python, TypeScript), chosen per language per problem. JVM stress cases run once per thread kind listed (`platform`, `virtual`), each a separate verdict.
- The CLI core expands templates (`$seq`, `$rand`, `$pick`, weighted `mix`) into literal per-worker scripts with seeded randomness, and evaluates invariants on a run record. Runners only execute, record outputs, run harness probes (`@enter`, `@exit`, `@pause`) and report `ok`, `error`, `invalid_output` or `stalled`.
- Correctness is invariant-based: equal multisets, distinctness, bounds, counts, sums, per-source order, probe-section violations and occupancy, and a content checker for the rest. Every invariant must hold on every schedule of a correct implementation.
- A case passes only if all N runs pass (`cstudy test`: 3 by default; `cstudy verify`: 10).
- Interleavings are widened deliberately: start gates; seeded yields between ops; in Python threads, `sys.setswitchinterval(1e-5)` and `sys.monitoring` yields at the user file's lines or instructions. Async schedules are deterministic per seed, so failing seeds reproduce.
- Each problem ships broken references (`solutions/broken/`), one or more per language. `cstudy verify` requires each to pass the sequential cases and fail its `caught_by` stress cases in at least 9 of 10 runs per language and variant. This makes the Phase 5 exit criterion a standing gate for every concurrent problem.
- PRD Q5: Kotlin coroutines are not autograded in v1; Kotlin uses threads, and coroutine designs are explanation content.
- TypeScript supports only the `async` model; problems whose race needs shared-memory threads omit TypeScript.

## Consequences

- A pass is evidence, not proof; the CLI says so on every concurrent pass.
- Detection power is measured, not assumed: scenarios are tuned until the broken references fail, and races that the GIL hides are documented and excluded from Python content.
- Runners stay small: no template or invariant logic, three additive protocol items (`features`, the `stalled` status, `restart_requested` with exit code 3).
- Verify cost grows: about 10 runs per reference, stress case and variant. Concurrent problems are exempt from the 30 s per-slug verify target.
- No bench, ladder, oracle or time limits for concurrent problems in v1.
- Content cost grows: broken references and their `### Bug`, `### Failing interleaving` and `### Fix` sections, which double as "spot the bug" exercises.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Linearizability checking (Wing and Gong, Knossos, Porcupine) | NP-complete in general, needs precise per-op invocation and response timestamps from three runtimes, and its counterexample histories are hard to read; targeted invariants catch the interview bug classes |
| Language-specific harnesses (jcstress, Lincheck, pytest plugins) | JVM-only or Python-only; breaks the one-format, language-neutral test model ([ADR 0001](0001-data-driven-tests.md)) |
| Deterministic schedulers or model checking for threads | Needs bytecode instrumentation or a custom scheduler per runtime; out of scope for v1 |
| Single run per case | Too weak: a lucky schedule passes broken code |
| Pass when most runs pass | Wrong for safety properties: one violation proves a bug |
| Scenario logic inside each runner | Three implementations of templating and invariants, as rejected for comparators in [runners](../specs/runners.md#decisions) |
| Autograding Kotlin coroutines (PRD Q5) | `suspend` functions break the JVM erasure property of the shared runner, need `kotlinx.coroutines` on the classpath and a Kotlin-only bridge; the multithreaded dispatcher fits neither model cleanly |
| TypeScript `worker_threads` with `SharedArrayBuffer` and `Atomics` | A class instance cannot be shared across isolates, and hand-rolled shared-memory classes are not an idiomatic TypeScript interview skill |
| No broken references, trust the scenario design | A scenario that never interleaves passes everything; nothing would detect it |
