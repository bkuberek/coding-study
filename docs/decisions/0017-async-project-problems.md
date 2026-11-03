# ADR 0017: Project problems grade asynchronous code on a virtual clock and concurrent code under stress

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-02 |
| Amended | 2026-11-02: the TypeScript clock helper offers `wait(promise)` besides `settle`, `advance` and `now`, the helpers Python's plugin offers, since a pending promise needs the clock moved while the test awaits it ([Runners](#runners)). 2026-11-02: spike K7 ran; Kotlin's clock sees only the test scheduler, so a wait that only another dispatcher can end is a deadlock at once, and a stress worker calls a `suspend` method in `runBlocking` on the real clock ([Runners](#runners)). 2026-11-02: spike K8 ran; tokio 1.53.3 is vendored with its macros, Rust's grader settles when the runtime's park hook runs, a wait whose sentinel timer fires first is a deadlock, and a spawned call holds the instance, so the entry class is shared from the first level that spawns a task ([Runners](#runners)) |
| Spec | [problem-format](../specs/problem-format.md#project-problems) (`async`, `project.clock`, harness operations, stress cases and broken overlays in projects), [runners](../specs/runners.md#project-jobs), [cli](../specs/cli.md#cstudy-submit) (`cstudy submit`, `cstudy new`, the [event stream](../specs/cli.md#event-stream)), [authoring](../specs/authoring.md#what-cstudy-verify-checks) (S18, D10, D6 and D7 for projects), [web-ui](../specs/web-ui.md#attempt-view), [toolchains](../guides/toolchains.md#go) |
| Amends | [ADR 0014](0014-project-problems.md) (projects gain asynchronous methods, a virtual clock and stress cases), [ADR 0006](0006-concurrency-stress-testing.md) (stress cases and broken references reach projects; Kotlin coroutines are graded in Kotlin projects, [PRD](../prd.md) Q5), [ADR 0012](0012-go-and-rust.md) (Go 1.25 or newer) |
| Builds on | [ADR 0001](0001-data-driven-tests.md), [ADR 0015](0015-local-web-ui.md), [ADR 0016](0016-jdk-range.md) |

## Context

A project problem is graded as a class job: the runner builds the entry class and calls the operations of a case in turn, and the core's `ops` comparator judges the outputs, which are scalars, arrays and lists ([ADR 0014](0014-project-problems.md)). The owner wants projects whose code is asynchronous or concurrent before more project problems are written. What the code base shows:

- Grading awaits nothing. Python and TypeScript encode the returned value as it is, so a coroutine and a Promise are `invalid_output` (`expected int, got coroutine`; `expected an int (32-bit integer), got a Promise`): `_OperationSequence` in `runners/python/src/cs_runner/jobs.py`, `OperationRun` in `runners/typescript/lib/execute.ts`. The JVM finds a method by name and arity, and a Kotlin `suspend fun` takes one more JVM parameter, a `Continuation` ([PRD](../prd.md) Q5). A Rust `async fn` returns a future that the generated bridge cannot encode. Go has no asynchronous functions: a Go method that waits blocks its goroutine.
- Time is an argument. Time-dependent behavior takes timestamps and never reads a clock ([operation sequences](../specs/problem-format.md#operation-sequences-design-problems)), so a project grades concurrency only as a simulation: the code computes what N workers would do at the times it is given. Real goroutines, threads, `async`/`await` and coroutines run only in your own tests, which `cstudy test` runs as feedback.
- Single-file problems already grade real concurrency ([ADR 0006](0006-concurrency-stress-testing.md)): stress cases that the core expands and judges by invariants, runners with start gates and perturbation, a deterministic `async` model in Python and TypeScript, the `stalled` status, a restart after threads are left behind, and broken references that D6 and D7 prove are caught. Check S14 keeps all of it out of projects (`cli/src/coding_study/domain/project_checks.py`).
- A project case that hangs meets the hang guard, 10 s by default, which kills the runner's process group and restarts it; the orphan guard ends the runner when `cstudy` dies ([runners](../specs/runners.md#hang-guard-and-restarts)). Projects have no bench and no time limit.
- The candidate projects are a Go build-graph runner on N workers, a message log with consumer groups and visibility timeouts, a TypeScript async event pipeline, a Kotlin coroutine service, a Rust async or thread-pool component and a Python asyncio service. Of the next three planned, the Python key-field store and the TypeScript spreadsheet need none of this, and the Go build-graph runner needs it only if its workers are goroutines rather than a simulation.

Spikes (scratch code, not merged), on the maintainer's laptop at a load average of 25 to 35, offline unless stated:

| Spike | Result |
|-------|--------|
| Go 1.27.3: `testing/synctest` in a module whose `go.mod` says `go 1.24` | Builds and runs, and `go vet -stdversion` is silent. `synctest.Test` and `synctest.Wait` are Go 1.25 API; the Go 1.24 experiment `synctest.Run` no longer exists; Go 1.27 adds `synctest.Sleep(d)`, documented as exactly `time.Sleep(d)` followed by `synctest.Wait()` |
| A build-graph runner whose 2 worker goroutines sleep each step's duration (5, 3 and 4 s), inside `synctest.Test` | Returns `b@3000 a@5000 c@9000` on every run; the 9 virtual seconds take 76 µs |
| Four goroutines that wake at the same virtual instant, 40 runs | 20 of the 24 possible orders appear, and 21 with `GOMAXPROCS=1`: the clock is deterministic, the order of simultaneous wake-ups is shuffled |
| The grading harness as a test binary: a `TestMain` reads cstudy's flags, and one test runs each case in a `synctest.Test` of its own | Works. A goroutine that waits on a channel forever panics `deadlock: all goroutines in bubble are blocked` at once; the harness recovers the panic and the next case runs, with the blocked goroutines left behind. A goroutine that waits on a held `sync.Mutex` is not durably blocked, so the clock stops and the case hangs until a wall-clock guard. After a one-line edit, a warm `go build` took 0.15 to 0.53 s and a warm `go test -c` 0.18 to 0.74 s (five each, noisy) |
| Python 3.13: an `asyncio.SelectorEventLoop` of 40 lines whose `time()` is virtual and whose selector moves the clock instead of sleeping, run through `asyncio.run(..., loop_factory=...)` | A service with a `Semaphore`, `wait_for` timeouts and sleeps gives the same result in 20 of 20 runs, 1.3 ms each; a task that awaits a future nobody resolves is reported at once (nothing ready, no timer). A pytest plugin of 30 lines, loaded with `-p` while plugin autoloading is off, runs `async def` tests on that loop. pytest 9.2 without a plugin fails every `async def` test |
| Node 24.18: `node:test`'s `mock` timers | Usable in the runner and in tests. `tick(20)` runs every timer due in the span with `Date.now()` at the end of the span, and a promise continuation that sets the next timer runs after the tick: after `tick(20)`, `await sleep(10); await sleep(10)` has run one step, stamped 20 instead of 10, and a second `tick(20)` ends it at 40 instead of 20. A static `import { setTimeout } from "node:timers/promises"` is mocked only after `syncBuiltinESMExports()`. A helper of 60 lines that records each timer's due time, ticks to the next one and lets promise continuations run before the following one gives every event its due time; 1,000 timer instants took 18 ms. At one instant, an interval callback ran before a promise continuation due at the same time |
| tokio 1.53.3, the newest release whose MSRV (1.71) is within cstudy's Rust 1.80, with `rt`, `time`, `sync`, `macros` and `test-util`, downloaded into a scratch `CARGO_HOME` | `#[tokio::test(start_paused = true)]` runs a 30 s visibility timeout in no measurable time. The closure is seven crates with 6.5 MB of sources, 4.3 MB without the macros, against the 2.3 MB vendored today. A task due at the instant the test's own `sleep` ended had not run when the test resumed; it ran once the test yielded. tokio 1.54 needs Rust 1.85 |
| K8: tokio 1.53.3 (MSRV 1.71; 1.54 needs Rust 1.85) with `macros`, `rt`, `sync`, `test-util` and `time`, vendored by `cargo vendor` from an empty `CARGO_HOME`, on Rust 1.92 (no 1.80 toolchain installed: every vendored crate declares `rust-version` 1.71 or older) | Seven crates; the vendored sources grow from 2.3 MB to 8.8 MB, 2.4 MB of it the macros' (`syn`, `proc-macro2`, `quote`, `unicode-ident`, `tokio-macros`), kept for `#[tokio::test]` and `select!`. tokio keeps `#[cfg(test)]` modules in `tests` directories under `src/`, which the runtime refresh would not copy while Cargo checks every file a checksum lists, so the trim drops them. A crate on tokio builds and runs a paused-clock test offline from a refreshed runtime with an empty `CARGO_HOME`. tokio has no call that waits until every task waits; the current-thread scheduler calls its `on_thread_park` hook exactly when no task is ready, none yielded and the `block_on` future was not woken, and only that park moves a paused clock, so a settle step woken by the hook ran a chain of 300 yields and of 500 tasks without moving the clock, and `@advance` as a `sleep` fired timers at 17, 24 and 31 ms on its way from 10 to 40 ms. A paused clock with nothing due parks for good, so a wait races a sentinel timer 2^35 ms ahead at a multiple of 2^30 ms, which the timer wheel fires in one step; a wait on a notification nobody sends ended at the sentinel, with the last idle park at the instant the last timer fired. `#[tokio::test]` cannot set the hook, so a test settles on the runtime's park count (`worker_park_count`, stable on 64-bit targets) from a blocking task, during which tokio holds the paused clock still: 100 of 100 runs agreed. An `async fn` taking `&mut self` is called through a closure whose future borrows the instance, and a spawned one through an `Arc` of it |
| Kotlin 2.4.21 | Not run: `kotlinx-coroutines-test` is in neither the Gradle nor the Maven cache, so it cannot build offline here. 1.11.0 is the current release of both coroutine libraries |
| K7: kotlinx-coroutines 1.11.0 (built with Kotlin 2.2.20) with Kotlin 2.4.21 and Gradle 9.8.2, fetched once from Maven Central | A bridge in Kotlin, a subproject of the runners' build compiled at release 21, runs each case as one coroutine on a `StandardTestDispatcher` and drives the scheduler with `advanceUntilIdle()`: a case still waiting when nothing is due is a deadlock, and a case whose calls left coroutines active fails as `runTest` fails a test. The conformance fixture's 10 cases took 0.24 s in one JVM, the first 62 ms of it loading the libraries. On JDK 21 and JDK 26 the fixture passes; a workspace warmed up before the change builds Java and Kotlin single files offline, refuses a Kotlin clock project offline with `run cstudy doctor --fix once while online`, and builds it offline after one online `doctor --fix`. A Kotlin subproject in the included build adds about 1 s to a Java build that misses the configuration cache, and nothing on a hit |

## Decision

### Three behaviors

A project grades three kinds of behavior, each with the determinism it can have:

| Behavior | What it grades | How it stays reliable | Languages |
|----------|----------------|-----------------------|-----------|
| Asynchronous methods | A method returns the language's awaitable; the grader awaits it before the next operation | As a synchronous call does: on the virtual clock, which a project with an asynchronous method must declare | Python, TypeScript, Kotlin, Rust; not Go, whose methods block, nor Java |
| The virtual clock | Code that sleeps, sets timers, times out, retries and runs background tasks, observed once it has settled | Time moves only when every task waits; no expected value depends on the order of events due at the same instant | Go, Python (asyncio), TypeScript, Kotlin (coroutines), Rust (tokio); not Java |
| Stress | Safety under real parallelism: lost updates, broken invariants, deadlocks | It is not deterministic: every one of N runs must pass, and broken references prove that the cases catch their bug classes (D6, D7) | All six, with the models of ADR 0006 |

- **One clock per problem.** `project.clock: virtual` puts every case of every level on the virtual clock, in grading and in the generated tests, from the constructor on, so a level that adds a timer to a level-1 method needs no other harness. A project without it runs on the real clock, as today, and its cases hold no harness operation and call no asynchronous method.
- **Asynchronous methods need the clock.** An asynchronous method on the real clock would grade the same values but turn every sleep and timeout into a real wait, so there is one mode, not two.
- **Stress cases belong to a level.** A stress case carries `level` as other cases do, calls only methods of its level and below, and may appear from the level whose statement first shares the instance between threads or tasks. Its level keeps at least 2 visible and 2 hidden sequential cases, which the statement's examples and the generated tests come from; stress cases stay hidden and are never generated as native tests.
- **Stress runs on the real clock.** In a virtual-clock project, a stress scenario calls only methods that wait on no timer.

### Format

`meta.yaml` gains two fields, and a project may have the `concurrency` block of ADR 0006:

```yaml
project:
  entry: log.log
  tests: tests
  clock: virtual        # every case runs on the virtual clock; without it, the real clock
signature:
  class:
    name: MessageLog
    constructor: {params: [{name: visibilityMs, type: long}]}
    methods:
      - {name: publish, level: 1, async: true, params: [{name: body, type: string}], returns: {type: long}}
      - {name: receive, level: 2, async: true, params: [{name: waitMs, type: long}], returns: {type: string}}
concurrency:
  model: async          # one string: a project lists one language
  runs: 3
  broken:
    - {id: unlocked-ack, name: Ack outside the lock, bug: "...", caught_by: [s1]}
```

- `async: true` marks a method that returns the language's awaitable: `async def` in Python, a `Promise` in TypeScript, `suspend fun` in Kotlin, `async fn` in Rust. The starter, the statement's `Methods to add:` line and the generated tests spell it so. `blocking` stays a modifier of concurrent problems.
- `project.clock` has one value, `virtual`; the real clock is the default and is never written.
- A broken reference of a project is an overlay, `solutions/broken/<id>/`, applied on top of the reference's overlay, with the changed files only.

`tests.json` gains four harness operations in the `ops` of a sequential case:

| Operation | Arguments | Output | Effect |
|-----------|-----------|--------|--------|
| `@advance` | `[ms]` | `null` | The clock moves `ms` milliseconds forward; each timer due on the way fires at its own time, and the code settles after each |
| `@spawn` | `[task, method, ...arguments]` | `null` | Starts the call without waiting for it, as the task named `task`: an asyncio task, a pending Promise, an `async` coroutine in the test scope, a spawned tokio task, or a goroutine in Go |
| `@join` | `[task]` | The call's result | Waits for the task, the clock advancing while every task waits; compared with the comparator of the method the task called |
| `@now` | `[]` | An integer | The virtual milliseconds since the case started |

```json
{"id": "ex3", "visible": true, "level": 2,
 "note": "a waiting receive takes a message published while it waits; an empty log answers after the wait",
 "ops": ["MessageLog", "@spawn", "@advance", "publish", "@join", "@now", "receive", "@now"],
 "args": [[30000], ["r1", "receive", 5000], [1000], ["a"], ["r1"], [], [2000], []],
 "expected": [null, null, null, 1, "a", 1000, "", 3000]}
```

- Harness operations begin with `@`, as a stress case's do, so no method name can clash with one. The format stays language-neutral: the four operations mean the same in every language that has the clock. Of the languages with the clock, only Go may `@spawn` a method that is not asynchronous, because only Go blocks a call instead of returning an awaitable.
- No new comparator. Settled code produces values: `unordered` covers results without an order, and no expected value depends on an order that the clock leaves open (below).
- Stress cases keep the schema of ADR 0006, with `level`.

### Semantics of a case on the virtual clock

1. **Every operation settles.** The grader calls the operation, awaits its result when the method is asynchronous, then waits until every task of the case is blocked (on the clock, on another task or on a pending call) before the next operation reads anything. Generated tests take the same step between operations; in Go it is `synctest.Wait()`.
2. **The clock moves only when every task waits.** While an operation waits for a result, time jumps to the next due timer, fires every timer due then, lets the code settle, and repeats until the result is ready. `@advance` moves the clock by its argument the same way; Go 1.27's `synctest.Sleep` is that operation.
3. **A deadlock is a verdict.** An operation that waits while no task can run and no timer is due ends the case at once as `stalled`, with its operation and the virtual time (`op 4 (@join r1): deadlock at 3000 ms`). Code that waits on what the clock cannot see (a lock whose holder waits, a busy loop, a thread, real I/O) never lets time move, and meets the hang guard as `timeout`.
4. **Simultaneous events have no order.** No expected value may depend on the order of events due at the same virtual instant, as no stress invariant may depend on a schedule. Go shuffles them at random (spike), asyncio leaves their order undefined, and Node does not guarantee it.
5. **Durations, not dates.** Each language's clock starts at its own epoch, so expected values hold durations from the case's start, which `@now` reads, never a reading of the clock. The problem's code reads time only through the clock that the language's facility controls: Go's `time` package, `loop.time()` in asyncio, `Date.now()` in TypeScript, the coroutine scheduler's time in Kotlin, tokio's `Instant` in Rust.
6. **A case ends as the language's test facility ends a test.** Go fails a case that leaves goroutines alive (synctest reports them as a deadlock), and Kotlin one that leaves coroutines active, as `runTest` does; Python, TypeScript and Rust drop pending tasks, as `asyncio.run`, Node and a dropped tokio runtime do. Content stops background work through the API before a case ends, and joins every task it spawns.

### Runners

Each language uses the virtual time its own ecosystem tests with, so the generated tests, your own tests and the grader run on one clock:

| Language | Grading | Generated tests and yours | Libraries and offline use |
|----------|---------|---------------------------|---------------------------|
| Go | A virtual-clock project's grading binary is a test binary (`go test -c`): a generated `TestMain` reads the runner's flags, and one test runs each case in a `synctest.Test` of its own and hands `runner.Main` the clock (settle, advance, now), so the runner package does not import `testing`. A recovered deadlock panic is `stalled`. Other projects keep `go build` | The body of each test in `synctest.Test(t, func(t *testing.T) { ... })`, `synctest.Wait()` between operations, `time.Sleep` and `synctest.Wait()` for `@advance`, a goroutine and a channel for `@spawn` and `@join` | The standard library, from Go 1.25, the first release with `synctest.Test`; a virtual-clock starter's `go.mod` says `go 1.25` |
| Python | Each case runs in `asyncio.run(..., loop_factory=VirtualClockLoop)`, the loop of a new module `cs_support.virtual_clock`: its `time()` is virtual, its selector moves the clock instead of sleeping, it breaks ties between timers due at the same instant by a seeded shuffle, and it reports a deadlock when nothing is ready and no timer is due. Asynchronous results are awaited | `async def` tests, which a pytest plugin in the same module runs on the same loop, with helpers `advance`, `settle` and `now`. The starter's `pyproject.toml` loads the plugin (`-p cs_support.virtual_clock` in `addopts`), since the runner turns plugin autoloading off | None new: `cs_support` is installed in every workspace venv from the runner runtime, which `cstudy` refreshes, so grading and tests share one implementation and no workspace needs a migration |
| TypeScript | `node:test`'s `mock` timers (`setTimeout`, `setInterval` and `Date`), driven by `runners/typescript/lib/virtual-clock.ts`: it records each timer's due time, ticks to the next one, and lets promise continuations run (one real macrotask) before the following one. It calls `syncBuiltinESMExports()` after enabling and after resetting the mocks, so a static import of `node:timers/promises` is mocked. Thenables are awaited | The same file, copied into the starter as `tests/virtual-clock.ts`, which the generated tests import and yours can: a project folder reaches no `#support` module. Its helpers are `settle`, `advance`, `now` and `wait`, which awaits a promise while the clock moves to each due timer. S15 keeps the copy byte-identical to the template's | None new: `node:test` ships with Node 24 |
| Kotlin (step 4) | A bridge written in Kotlin, the runner module `cs.coroutines`, calls `suspend` methods, passing the extra `Continuation` of their JVM signature, on a `kotlinx-coroutines-test` scheduler. `cs.runner.Main` finds it with `ServiceLoader` on the classpath of a project that applies the `cs.coroutines` plugin, as it finds `cs.suite`. The clock sees only the test scheduler: code that moves to another dispatcher runs on the real clock, and a wait that only such code can end is a deadlock at once, where `runTest` would wait for real. A stress worker calls a `suspend` method in `runBlocking`, on the real clock | `runTest { }`, `runCurrent()` between operations, `advanceTimeBy` then `runCurrent()` for `@advance`, `async { }` for `@spawn` | `kotlinx-coroutines-core` and `kotlinx-coroutines-test` at the release the pinned Kotlin supports (1.11.0 today), in the runners' version catalog. The `cs.coroutines` plugin adds them and the starter applies it; the Kotlin warm-up project of `cstudy doctor --fix` applies it too, so they are cached for offline builds as JUnit is ([ADR 0014](0014-project-problems.md#java-and-kotlin-spike-k4)). Their class files, and the module's at release 21, load on every JDK of ADR 0016's range |
| Rust (step 5) | The bridge runs each case on a current-thread tokio runtime built with the clock paused, and awaits `async fn` results on it. Spike K8: settling waits for the runtime's park hook, `on_thread_park`, which runs exactly when every task waits; a wait races a sentinel timer about 400 days ahead, and one that the sentinel ends is a deadlock at the virtual time of the last idle park. `@spawn` hands a call to `tokio::spawn`, and since the call holds the instance, the entry class is shared from the first level that spawns, as from the level that adds stress cases; a stress worker blocks on an `async fn` on the real clock | `#[tokio::test(start_paused = true)]`, with a settle helper defined once in the file. Spike K8: `#[tokio::test]` takes no park hook, so the helper waits on the runtime's park count from a blocking task, during which tokio keeps the paused clock still | tokio, vendored with `rt`, `time`, `sync` and `test-util` (and `macros`, unless spike K8 drops them) at the newest release whose MSRV is at most cstudy's Rust 1.80 (1.53.3 today), pinned exactly as `rust_decimal` and `chrono` are and allowed in a starter's `Cargo.toml` |
| Java | No virtual clock and no asynchronous methods: `java.time`, `Thread.sleep` and the executors read the real clock, and nothing in the JDK replaces it without the code's help. Java projects get stress cases (step 3) | | |

`hello.features` gains `clock` (the virtual clock, its harness operations and asynchronous methods) and `project-stress`, and `cstudy` refuses such a job to a runner without them (exit 4), as it does for `project` and `suite`. The JVM runner lists `clock` only when `cs.coroutines` is on its classpath.

### Stress cases in projects

- **The grading job carries them** as a concurrent job does, and each runner runs them with its existing stress code on the project's entry class. Python's line and instruction perturbation, which yields in the target file today (`runners/python/src/cs_runner/perturbation.py`), yields in every file under the project root. The JVM runs each thread kind that `jvm_threads` lists, and ADR 0016's rule holds: a stress case and a broken overlay must hold on every JDK of the problem's range. Go's stress workers keep reflection, as for single files. Rust's bridge registers the entry class as concurrent, so its methods take `&self` from the level that adds stress cases, and a `&mut self` method is a load error that says why. TypeScript, and Python with asynchronous methods, use the `async` model.
- **Broken overlays are proven as broken references are.** `cstudy verify` builds each one in `.cs/build/projects/<slug>/broken-<id>/` (the starter, the reference's overlay, then the broken one). D7 requires it to pass every sequential case and to fail each of its `caught_by` stress cases in at least 9 of 10 runs; D6 requires the reference to pass every stress case in 10 of 10 runs, the slowest under 25% of its deadline. The `## Broken: <id>` sections of the explanation and `cstudy solution --broken` work as for concurrent problems.

### Determinism and flakiness

- **Virtual time wherever code waits.** No case waits on the wall clock, which serves only as the hang guard.
- **D10, a determinism check.** `cstudy verify` runs every case of a virtual-clock problem 10 times on the reference. Every run must give the same outputs, and the slowest must stay under 25% of the problem's hang guard. Go's runtime shuffles simultaneous wake-ups, and Python's loop shuffles tied timers by seed (seeds 0 to 9 in D10, seed 0 in grading and in your tests, so the two agree), so a case whose expected values depend on a tie fails D10 there. TypeScript's mock timers and Kotlin's test scheduler fire tied events in the order they were scheduled, so D10 cannot see a tie in those languages, and the rule holds there without a check.
- **One run per submission.** A virtual-clock case runs once in `cstudy submit`: it takes microseconds to milliseconds, and its only nondeterminism is Go's shuffle, under which code that depends on a tie is as flaky as it is under `go test`.
- **Stress keeps ADR 0006's thresholds and the busy-machine warning**: correct references pass 10 of 10 runs per variant, broken ones fail at least 9 of 10, the slowest correct run stays under 25% of `deadline_ms`, and a failure while the load is above half the cores names the load. A project lists one language, so its stress runs never compete with another language's.

### Time limits and hangs

- **No per-operation timeout.** A wait ends at a virtual time the expected values fix, deadlocks (`stalled`, at once), or never lets the clock move (`timeout`, by the hang guard).
- **The hang guard stays per case**: the case's `hang_guard_ms`, else `limits.hang_guard_ms`, else 10 s. A correct virtual-clock case takes milliseconds, so the author lowers `limits.hang_guard_ms` to a few seconds and D10 keeps the margin; a submission that hangs fails within it, and after 3 restarts the remaining cases are `not_run`, as today.
- **A fresh process after a deadlock.** After a `stalled` case that leaves goroutines (Go) or threads behind, the runner writes `restart_requested` and exits 3, so the next case starts in a fresh process; these restarts do not count against the 3 crash restarts, as for stress runs. A `timeout` still counts.
- **The process lifecycle does not change.** Go's test-binary harness is the runner process: `cstudy` starts it in a process group of its own with an orphan guard, and it starts no process. SIGINT and SIGTERM end a submission as before. Stress runs keep `deadline_ms` and their hang guard of `deadline_ms + 5000`.
- **No bench and no performance limit.** Projects keep ADR 0014's rule; grading asynchronous and concurrent code needs neither.

### What you see

- `cstudy test` runs the native suite as before. The generated files use the language's virtual clock, so the visible cases run natively as they are graded; a native deadlock shows as the framework reports it (in Go, the test binary panics with `deadlock: all goroutines in bubble are blocked`, which the suite reports as that test's `error`).
- `cstudy submit` prints asynchronous and virtual-clock cases as any case, and a deadlock as a `STALLED` row that names the operation and the virtual time. Stress cases print under their level, one line per case and variant with its runs and failing seeds, as `cstudy test` prints them for a concurrent problem, and the summary adds `stress runs found no race (not a proof of thread safety)`. A mock attempt counts failing hidden cases, stress cases included, and shows nothing else, as before.
- `--json` and `--events`: a project case can be `stalled`, with `op_index` and `reason`; the submission's document gains `stress`, each entry with its `level`; the stream gains `stress_run_start`, `stress_run` and `stress_result` in `cstudy submit`, each with a `level`; and `level_result` counts stress verdicts as hidden cases. Every change is additive, so the stream stays at version 1.
- The web UI draws stress rows with their run dots inside the level's group of a submission, as it draws them for a concurrent problem's test run, and `STALLED` case rows. The statement renders an example's harness operations in words (`r1 = receive(5000) starts`, `1000 ms pass`, `r1 returns "a"`, `the clock reads 1000 ms`), `## Project` gains a generated line that names the virtual clock, and a level section with stress cases gains the stress table that a concurrent problem's `## Concurrency` section has.
- `cstudy test --debug` gains one property: a breakpoint does not move the virtual clock, so no timeout fires while you inspect the code.

### Authoring and checks

- `cstudy new --from-template project-<language>` keeps its synchronous two-level template. `--virtual-clock` writes the variant: `project.clock: virtual`, a level-2 method that waits (asynchronous where the language has the form), an example with `@spawn`, `@advance`, `@join` and `@now`, the starter's clock pieces and a README section on testing on the clock. `--stress` adds a `concurrency` block, one stress case at level 2 and one broken overlay, as a directory of changed files laid over the template (or its clock variant), so the build files that S15 compares exist once. Each flag exits 3 for a language its step has not reached, and `--stress` for TypeScript without `--virtual-clock`: its stress cases run in the `async` model, where a synchronous method is atomic and an asynchronous one needs the clock.

The checks, new and changed:

| Check | Rule |
|-------|------|
| S18 (new) | `async` only on methods of a project in Python, TypeScript, Kotlin or Rust, and only with `project.clock: virtual`; `project.clock: virtual` only in Go, Python, TypeScript, Kotlin or Rust. Harness operations only with the virtual clock, with valid arguments: `@advance` from 1 to 2,147,483,647 ms (Node's largest timer delay); `@spawn` a task name unique in its case and a method of the case's level or below with its arguments, an asynchronous method outside Go; `@join` a task spawned earlier and not yet joined; `@now` none. Every spawned task is joined. Expected values: `null` for `@advance` and `@spawn`, the method's result type for `@join`, an integer for `@now`. Ties are content's to avoid; no static check finds them |
| S14, S15, S16 (changed) | A project may have stress cases, a `concurrency` block whose `model` is one string valid for its language, and broken overlays, and S11 and S12 apply to them. S15: a virtual-clock starter in Go declares `go 1.25`, in Python its `pyproject.toml` loads `cs_support.virtual_clock`, in TypeScript it holds `tests/virtual-clock.ts` as the template writes it, and in Kotlin it applies `cs.coroutines` |
| D6, D7 (extended) | Run on a project's stress cases, with its reference and its broken overlays |
| D9 (unchanged) | Now also proves that the generated virtual-clock tests pass natively against the reference |
| D10 (new) | Every case of a virtual-clock problem gives the same outputs in 10 runs of the reference, the slowest under 25% of the hang guard |

The ready criteria add D10 for a virtual clock, and for stress cases ADR 0006's: at least 2 stress cases, at least one broken overlay, and every broken overlay caught.

### Scope and order

Each step is one language family, so one pilot problem proves each before the next starts:

| Step | What lands | Unblocks | Before it |
|------|------------|----------|-----------|
| 1 | Go: the virtual clock, the harness operations, `stalled` on project cases, S18, D10, Go 1.25 | The Go build-graph runner on goroutines | Nothing more: this ADR's spikes settle it |
| 2 | Python and TypeScript: asynchronous methods on the virtual clock | The TypeScript event pipeline, then the Python asyncio service | Nothing more |
| 3 | Stress cases and broken overlays in projects, in all six languages | The message log's concurrent consumers, the Rust thread pool | Nothing more |
| 4 | Kotlin coroutines | The Kotlin coroutine service | Spike K7: both coroutine libraries offline through `doctor --fix` on JDK 21 and 26, the `suspend` bridge, and stress workers that call `suspend` methods |
| 5 | Rust async on tokio | The Rust async component | Spike K8: vendoring with or without the macros, and a settle step, which tokio's API lacks |

- **The minimal version** changes nothing for the Python key-field store and the TypeScript spreadsheet. The Go build-graph runner needs step 1 if its workers are goroutines; as a simulation driven by explicit timestamps it can be graded today.
- **Pilots**: the build-graph runner (Go, step 1), the event pipeline (TypeScript, step 2; Python follows with the same format), the message log (step 3), the coroutine service (Kotlin, step 4) and an async component (Rust, step 5).

## Consequences

- Existing problems do not change: a project without `project.clock` and stress cases grades as today, and its starter and generated files stay as they are.
- New surface: the `async` modifier, `project.clock`, four harness operations, stress cases, a `concurrency` block and broken overlays in projects, `stalled` on project cases, stress events with a `level` in `cstudy submit`, checks S18 and D10, the `clock` and `project-stress` runner features, `cs_support.virtual_clock`, the TypeScript clock helper, the `cs.coroutines` plugin and module, and the vendored tokio.
- Go's minimum rises from 1.24 to 1.25 for every workspace (`MINIMUM_GO` in `cli/src/coding_study/application/doctor.py`, the toolchains guide), because `synctest.Test` is Go 1.25 API; Go 1.24 and 1.25 are both past their upstream support. A workspace on Go 1.24 upgrades before its next Go run, and a `go.mod` that says `go 1.24` keeps building.
- The grading binary of a virtual-clock Go project links `testing`, since it is a test binary; the spike put its warm build within the range of `go build`.
- PRD Q5 changes for projects: a Kotlin project may declare `suspend` methods (step 4). Single-file concurrent problems keep threads.
- The Rust runtime's vendored sources grow from 2.3 MB to 8.8 MB, with the macros (step 5, spike K8).
- NFR-1: a submission's stress runs are outside the project targets, as a concurrent problem's stress runs are outside its targets; asynchronous and virtual-clock cases are inside them and cost microseconds to milliseconds each. D6, D7 and D10 runs are outside NFR-3's 30 s per problem.
- NFR-6 holds: Go, Python and TypeScript add nothing to download, tokio is vendored, and Kotlin's two libraries are cached by `cstudy doctor --fix`, which needs the network once, as JUnit did.
- The content rule that time-dependent behavior takes timestamps as arguments now applies to problems without a virtual clock only.
- Stress levels cost content work as concurrent problems do: broken overlays and their explanation sections.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| A Java project needs timeouts or scheduling | A harness-provided `java.time.Clock` and `ScheduledExecutorService` that the entry class receives, as a new signature type |
| Authors need event logs whose simultaneous events have no defined order | A comparator ordered by time and unordered within an instant |
| A Go level opens on a lucky schedule in practice | Running each virtual-clock case several times per submission, as stress cases run |
| A project needs stress on code that waits on its clock | Stress runs on the virtual clock: goroutines in a bubble in Go, and the event-loop languages' clocks |
| Users need to rerun one failing stress seed of a project | `cstudy submit --stress N --seed S`, as `cstudy test` has for concurrent problems |
| A pinned Kotlin or Rust release needs a newer coroutine library or tokio | Moving those pins with the toolchain's |
| Node's mock timers advance through promise continuations or report the next due time | Dropping the bookkeeping of the TypeScript helper |
| A project wants a level that turns a synchronous method asynchronous | `async` per level |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| The real clock with tolerances | Slow (a 30 s timeout takes 30 s) and flaky on a busy machine, where a timer fires late |
| Time as arguments only, as today | Grades a simulation of concurrency, not the code: the limitation this ADR removes |
| Grading through the native framework, with hidden tests generated into a private copy | The framework's assertions would judge: the second judge that ADR 0010 and ADR 0014 rejected, and the agreement exceptions of generated tests would become verdicts |
| A comparator over timed event logs | Content can answer per item (a step's finish time); the comparator would need generated-test support in six languages first |
| Harness-provided collaborators: fakes that the entry class calls and the case resolves | A new signature type, an interface per language, and generated implementations in Go and Rust; durations given as data cover the planned projects |
| Scenario cases on the virtual clock: stress's setup, workers and final, run once and compared exactly | Worker scripts do not turn into readable native tests or statement examples; `@spawn` expresses concurrent callers inside the operation sequence |
| An explicit `@settle` operation | Every observation would need one; settling after each operation is what `synctest.Sleep` and `runCurrent()` do |
| A clock per case | Generated tests cannot tell which methods wait, and a level that mixes clocks is hard to state |
| Asynchronous methods on the real clock as a second mode | Every sleep and timeout becomes a real wait, for no gain over the virtual clock |
| Every project on the virtual clock | A test binary for every Go project and clock code in every generated test, for problems that never wait |
| Go: `synctest.Run` from a plain binary | The Go 1.24 experiment, which Go 1.27 no longer has |
| Go: a minimum per problem | ADR 0016 keeps toolchain minimums workspace-wide for Go and Rust, and Go 1.24 is past its upstream support |
| Go: `-race` in grading | Needs cgo and a C toolchain on Linux, so a verdict would depend on the machine |
| Python: pytest-asyncio with a fake-time plugin | Two more packages in the shared venv, which existing workspaces would install online, and the grader's loop would still differ from the tests' |
| Python: generated tests that call `asyncio.run` from synchronous functions | A nested function in every test, which your own tests would copy; the plugin keeps plain `async def` tests |
| TypeScript: `mock.timers.tick(ms)` as Node offers it | Callbacks see `Date.now()` at the end of the span, and promise chains restart from it (spike) |
| TypeScript: fake timers of the runner's own, mock timers in the tests | Two clocks that can disagree on the same case |
| TypeScript: ticking 1 ms at a time | Exact only with a macrotask per millisecond: 30,000 ms took 4.1 s on the loaded machine |
| Kotlin: coroutines on `Dispatchers.Default` with the real clock | Real waits, so slow and flaky; the test scheduler is the language's own answer |
| Rust: a standard-library `block_on` without tokio | Asynchronous Rust needs a runtime to sleep, spawn and time out, and tokio is the one its code uses |
| Java: `CompletableFuture` methods awaited on the real clock | Without a clock to control, an asynchronous Java method grades nothing a blocking one does not; stress grades Java's concurrency |
