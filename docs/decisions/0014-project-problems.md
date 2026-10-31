# ADR 0014: Project problems are seeded folders in one language, solved in levels

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-30 |
| Amended | 2026-10-31: [Go project problems](#go-spike-k5), after spike K5; [Java and Kotlin project problems](#java-and-kotlin-spike-k4), after spike K4 |
| Spec | [problem-format](../specs/problem-format.md#project-problems), [runners](../specs/runners.md#project-jobs), [cli](../specs/cli.md#cstudy-submit), [authoring](../specs/authoring.md#project-problems), [installation-and-workspaces](../specs/installation-and-workspaces.md#project-folders), [progress-and-scheduling](../specs/progress-and-scheduling.md#project-attempts) |
| Amends | [ADR 0001](0001-data-driven-tests.md) (native test files generated from the data), [ADR 0012](0012-go-and-rust.md) (a fourth exception to the six-language rule) |

## Context

Every autograded problem today is one file per language: `cstudy start` generates a stub from the signature, and the runner loads that one file ([ADR 0001](0001-data-driven-tests.md)). A progressive problem grows one class over levels, and a run of `cstudy test` that passes every case of the unlocked levels opens the next one. That covers an API that grows, but not the work of building and extending a small codebase: splitting it into modules, adding files, writing your own tests and running them with the language's own tools. The owner wants that exercise, and wants a web interface on top of it later.

What the code base showed before the decision:

- The Python runner executes one file as a module of its own, so a package-relative import in a second file fails (`ImportError: attempted relative import with no known parent package`). The TypeScript runner imports by file URL, so relative imports already resolve.
- Java, Kotlin and Go already compile every file of a problem's package directory; Rust compiles one file as a `#[path]` module.
- Tests are language-neutral data so that one case set serves six languages and the statement's examples come from the same cases as the grade. IDE-native tests were rejected as a second judge in [ADR 0010](0010-ide-integration.md).
- A catalog problem lists every language that can express it ([ADR 0012](0012-go-and-rust.md)), with three exceptions.

A spike (scratch code, not merged) built a two-file bank in Python and TypeScript. pytest and `node:test` both ran in-process from a host script outside the project and reported each test as it started and ended, with the assertion detail; the runner-side cost was 0.12 s for pytest with warm bytecode (0.54 s cold) and 0.06 s for `node:test`. A second spike (K1) settled the Python folder: a relative `.venv` link to the shared venv works for pyright, basedpyright and pytest, a `requires-python` above the venv's Python makes `uv run` delete the shared venv through that link, and a user file such as `random.py` shadows the standard library when the project root comes first on `sys.path`.

## Decision

- **A new kind.** `kind: project` on the `practical` track: a folder of seeded files (`starter/`) that `cstudy start` copies to `projects/<slug>/` in the workspace. Levels, level cases and the `ops` comparator work as for progressive problems and share one level module; the kind gets its own branch in every exhaustive `match` on `ProblemKind`.
- **One language per problem.** A project problem lists exactly one language and is solved only in it. A version in another language is a separate problem, built from scratch with its own id, slug, starter, cases, reference and explanation; only the statement wording may be reused. Siblings link through `related`, and the slug carries the language (`bank-project-python`), since slugs key progress. This is a fourth exception to the six-language rule of ADR 0012: check S13 skips `must list` for the kind.
- **`tests.json` stays the single source.** Its cases feed the statement's examples, the visible native tests and the grade. `cstudy` generates one native test file per level from that level's visible cases (pytest, `node:test`, JUnit 5, kotlin.test), at start for level 1 and at each unlock for the next level, and never rewrites one. Authors may ship extra test files in the starter, and users add their own.
- **Two commands.** `cstudy test` runs the native suite: the generated files, the starter's and your own. It is feedback only, never a grade, and opens nothing. `cstudy submit` sends every case of the unlocked levels, visible and hidden, through the runner protocol; the core's comparator judges each output, and a submission that passes every one opens the next level. Editing a generated test file never changes a grade.
- **Levels stay hidden until they open.** The starter holds only level 1's methods. Each unlock reveals the next statement section, which names the methods to add, and the grader checks only the methods of the levels it grades.
- **Hidden cases.** A failing hidden case shows its input, expected and actual in a practice attempt, and only a count in a mock attempt.
- **Grade.** `cstudy done` takes a rating once level 1 passes and caps the grade by the levels finished: all levels, no cap; all but the last, `hard`; fewer, `again`. The time box stays soft: finishing over it caps the grade at `hard`, as today.
- **One final reference.** Each project problem has exactly one approach, whose reference is an overlay on the starter (`solutions/<approach>/`, changed and added files only) implementing every level. No snapshot per level.
- **Runners host the framework.** The Python, TypeScript and JVM runners learn to load a project folder for grading and to run the native framework in-process as a new `suite` job, so a test gets the runner's hang guard, output capture, crash restart and debug launch. Go runs its test binaries as child processes of the runner instead, with the same guarantees ([Go](#go-spike-k5)).
- **Shared toolchains.** A project folder reaches the workspace's toolchain by relative path: the Python venv and Node installs, the vendored Go modules, and on the JVM the workspace's Gradle wrapper, daemon and runner runtime. Nothing is installed per project, so a Python, TypeScript or Go project starts offline (NFR-6). A Java or Kotlin project starts offline once `cstudy doctor --fix` has cached JUnit, kotlin-test and their dependencies, which no single-file problem needs ([Java and Kotlin](#java-and-kotlin-spike-k4)).
- **Python and TypeScript first.** Rust project problems are not yet supported, and `cstudy verify` rejects one; Go followed after spike K5 ([below](#go-spike-k5)), Java and Kotlin after spike K4 ([below](#java-and-kotlin-spike-k4)). Each needed a build of its own per project (a Gradle build, a Go module, a Cargo crate) and a spike before it was specified:

  | Language | Open question | Spike |
  |----------|---------------|-------|
  | Java, Kotlin | Settled by K4: a standalone Gradle build per project folder on the shared daemon, within NFR-1 without a persistent runner ([below](#java-and-kotlin-spike-k4)) | K4 |
  | Go | Settled by K5: one module per project with a `go.work` of its own in the folder, never an entry in the root `go.work`; the overlay registration works inside a project package ([below](#go-spike-k5)) | K5 |
  | Rust | `cargo test` results on stable Rust without libtest's JSON output; two profiles (tests in dev, grading in release) compiled per change; a harness that depends on the project crate by path | K6 |

### Go (spike K5)

Spike K5 (scratch code, not merged) built a two-package Go bank with a test file per level, own tests, subtests, parallel tests and an Example, on Go 1.27 and Delve 1.27.2. Go project problems follow its design ([problem-format](../specs/problem-format.md#project-problems), [runners](../specs/runners.md#go-project-jobs), [installation-and-workspaces](../specs/installation-and-workspaces.md#project-folders)):

- **A module per folder, with a `go.work` of its own.** The starter's `go.mod` declares `module <slug>` (check S15) and reaches the vendored decimal module through `replace ../../.cs/runtime/runners/go/third_party/...`, so it needs neither a `go.sum` nor the network. `cstudy start` writes `projects/<slug>/go.work` holding `use .`, through which gopls and `go test ./...` in the folder resolve imports. The root `go.work` is left alone: a `use` line there breaks every go command once an archive moves the folder, and two folders with one module path fail with `module appears multiple times`.
- **Grading** builds a runner binary per project against a `go.work` of its own in the build directory, which joins the build module `csbuild` and the project folder. The registration and thunk files enter the entry's package through `go build -overlay`, as for a practice file; overlay and typed thunks work for a package spread across files and subpackages. The thunks cover the methods of the graded levels only. Measured: 0.23 to 0.37 s p50 of toolchain time.
- **Suite.** The runner runs `go test -json -count=1 -timeout=0 ./...` in the folder as a child process and turns its events into suite results. This corrects "Runners host the framework" for Go: the tests run in test binaries, not in the runner's process, yet the hang guard, output capture, crash restart and debug launch still work through the child. Parsing the native report is fine here, unlike JUnit XML in the alternatives below, because `go test -json` is the go command's documented interface and reports each test as it starts and ends. Measured: 0.53 to 0.69 s p50.
- **Hang guard and restarts.** `-timeout` covers a whole test binary, not a test, so the hang guard times the gap since the last `go test` event, `t.Parallel` tests pausing and finishing late, and the CLI's watcher kills the process group. A test binary that panics or calls `os.Exit` ends with the test it was running, which is reported as an `error`; the runner runs that package again with `-skip` of the top-level tests already reported, so a panic, which a starter's `not implemented` methods raise in every test, never uses up the CLI's crash restarts. A restart after a hang passes `-skip` the same way, with the culprit: one regular expression cannot name an arbitrary set of subtests, so both leave out whole top-level tests.
- **Debug.** The runner builds the test binary with `-gcflags=all=-N -l`, runs it under `dlv exec --headless`, and pipes its output through `go tool test2json`; breakpoints in the project's code and in its tests stop.
- **Speed.** A Go project's `cstudy test` takes about 1.2 to 1.4 s end to end, over the 1.0 s that NFR-1 sets for Python and TypeScript projects, so NFR-1 gives Go projects a target of their own, 1.5 s.

### Java and Kotlin (spike K4)

The question K4 answered: the warm p50 of compiling a project's main and test sources plus a JUnit Platform launch, against NFR-1's 3 s (Java) and 5 s (Kotlin); JUnit resolved offline; locks and per-run class copies per project build. ADR 0007 names multi-file problems as its revisit trigger.

Measured on an M3 Pro (JDK 21.0.2, Gradle 9.8.2, Kotlin 2.4.21, JUnit 5.14.4), warm p50 after a one-file edit, for three routes:

| Route | Java | Kotlin | Verdict |
|-------|------|--------|---------|
| (a) One shared Gradle build, a source set per project | Similar to (b) | Similar to (b) | Rejected: adding a project costs 1 to 1.8 s once and invalidates the configuration cache of every JVM build; VS Code folds every project into one Eclipse project, so packages clash; Kotlin tests cannot see `internal` declarations |
| (b) A standalone Gradle build per project folder, on the shared daemon | 0.61 to 0.64 s build and launch (about 1.0 s with `cstudy`'s own 0.4 s) | 1.26 to 1.41 s (about 1.8 s) | **Chosen**: a third of the targets |
| (c) `javac` and `kotlinc` called directly | Similar | 2.6 to 4.7 s: every run starts a cold compiler with no incremental compile | Rejected |

- **A Gradle build per folder.** `projects/<slug>/` holds its own `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and `gradle/wrapper/gradle-wrapper.properties`, and `src/main/<java|kotlin>` and `src/test/<java|kotlin>`. Its settings find the workspace by walking up to `.cs/workspace.toml`, never by a fixed `../..`, because the same files also build in `.cs/build/projects/<slug>/<approach>/`. They take the workspace's version catalog and include the runtime's `runners/jvm` build, whose `cs.project` plugin sets the JDK, JUnit and the runner. This is the route that rejects project folders inside the language projects (see the alternatives).
- **Build and run.** `cstudy` runs `<ws>/jvm/gradlew -p <folder> --offline` on the shared daemon: `csClasspath` writes the main and test runtime classpaths before a suite, `csMainClasspath` the main one before grading, so a test file that does not compile never blocks a submission. One exclusive lock per project build (not per language), the existing runtime lock and the per-run class copy keep concurrent `cstudy` processes apart; their cost is in the timings.
- **Suite.** `java -cp <test runtime classpath> cs.runner.Main` hosts the JUnit Platform Launcher with a listener that writes protocol events: framework `junit-platform`, JUnit Jupiter for Java and kotlin.test on JUnit 5 for Kotlin. Test ids name the file first, as pytest's and `node:test`'s do (`src/test/java/bank/Level1Test.java::ex1`, with `[n]` per parameterized invocation), read from the class file's `SourceFile` attribute: the spike's `pkg.Class::method` named no file, and the CLI tells a generated test from the starter's and from yours by its file. A failed assertion's expected and actual are the strings opentest4j carries, not JSON values. A class whose `@BeforeAll` fails is reported once, under the class's id, so a restart's `skip` prunes by class as well as by test.
- **Grading.** The class job of every JVM problem, on the main runtime classpath; the target is the entry class (`bank.Bank`).
- **Offline.** `cstudy doctor --fix` builds one warm-up project per language from the template, which caches JUnit, kotlin-test and `apiguardian-api` (a resolvable prefetch configuration missed `apiguardian-api`, which only JUnit's compile variant brings). The first build of a new folder takes 1.5 to 2.4 s on a warm daemon.
- **No persistent JVM runner.** [ADR 0007](0007-no-persistent-jvm-runner.md)'s trigger is not met, and the Kotlin Gradle plugin already keeps a compile daemon of its own.

## Consequences

- A project problem has no generated stub, no generator, no bench, no oracle and no time limit: `cstudy bench`, `cstudy test --perf`, `--stress` and `--time-limit`, and `cstudy verify --oracle` and `--ladder`, do not apply to it.
- Coverage lines and `--lang` filters count a project only in its language. The catalog grows one problem per language version, and each version costs a full authoring pass; the TypeScript pilot measures that cost.
- New CLI surface: `cstudy submit` and `cstudy status`, a `projects/` folder in every workspace, pytest in the workspace's Python template, `submissions` and `level_unlocks` tables, verify checks S14 to S16 and D9, and the `cstudy doctor` rows on the JVM project libraries.
- The Python runner gains a package-aware loader that compiles project modules from source on every run and keeps library bytecode under `.cs/pycache/`, and one runner process per project job, since two projects may both define a top-level `bank` module.
- The runners' JVM build gains the `cs.project` Gradle plugin, which every Java and Kotlin project folder applies, and `cs.suite`, the JUnit Platform host that only a project's test runtime classpath holds. A Java or Kotlin starter's build files are exactly the template's, with its slug as the root project's name (check S15), so every folder builds the same way and offline.
- The JVM warm-up of `cstudy doctor --fix` resolves the runtime classpath (`csClasspath`) and builds the warm-up projects. K4 found that the warm-up before it compiled classes only, so a fresh Gradle home never cached the runner's own `gson` and no Java or Kotlin problem, single-file ones included, built offline.
- A starter's `pyproject.toml` holds tool tables only. A `[project]` table, `requires-python` or `[tool.uv]` in it could make `uv run` delete the shared venv, so check S15 rejects them.
- A Go project folder is a module of its own whose `go.work`, like a Python folder's `.venv` link, is untracked: `cstudy start` writes it when it is missing and `cstudy doctor --fix` restores it. `cstudy doctor` also warns about a vendored `replace` that does not resolve and about two folders with one module path. A generated Go level file that calls a method not written yet stops its whole package from compiling, as any Go test would; `cstudy test --level` leaves it out.
- The pilots are `0249-bank-project-python`, then `0250-bank-project-typescript`, with the behavior of `0248-scheduled-transfers-bank`. 0187 and 0248 stay progressive, since converting them would remove their six-language versions.
- The web interface is still a PRD non-goal; the project folder, `cstudy submit --json` and `cstudy status --json` are the boundary it would build on.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| Spike K6 reports | Specify Rust's project folder, suite and grading, amending this ADR |
| The warm p50 of a Java or Kotlin project, measured as [ADR 0007](0007-no-persistent-jvm-runner.md) measures, exceeds two thirds of its NFR-1 target | ADR 0007's levers for the project build: skip Gradle when nothing changed, then a compile server |
| The owner finds the pilot's generated tests read like machine output | Hand-written visible tests in the starter, kept next to `tests.json` (alternative C below) |
| Ports become frequent, or a third language version of one project is wanted | Sharing cases between siblings, and a `variant_of` field so that `cstudy start bank-project --lang typescript` works |
| Seeing the code evolve proves worth about four times the reference work | A reference snapshot per level, shown by `cstudy solution --level N` |
| The web interface is scheduled | The PRD non-goal and the absence of a sandbox for user code |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| A `layout: project` flag on `progressive` | Projects differ in layout, start, grading, references, verify, bench and languages; a flag hides those branches from the exhaustive `match` on `ProblemKind` |
| Every project in all six languages, as ADR 0012 requires of other problems | Different languages suit different projects, and a folder's layout, build files and idioms do not translate the way one function does |
| A. Hand-written native visible and hidden tests | The verdict would come from a framework running over code the user can edit: the second judge ADR 0010 rejected. Examples in the statement would be written by hand a second time |
| B. `tests.json` only, nothing to run natively | Misses the point of the exercise: running your code with the language's own tools |
| C. `tests.json` for grading, hand-written visible tests in the starter | Every visible case written twice, as data and as test code; verify proves both pass the reference, not that they agree. Kept as the fallback |
| Every `cstudy test` grades hidden cases and opens levels, as for progressive problems | Skips the loop being practiced: testing your own edge cases before you submit |
| A level opens once its visible tests pass; submissions only score | The visible tests are editable, so a level would open on the user's own verdict |
| Every method stubbed in the starter from level 1 | Designing for changes you cannot see yet is the point of a staged project |
| Project folders inside the language projects (`python/projects/<slug>/`) | Inherits the venv and `node_modules` without configuration, but is not one folder on the JVM, and Go and Rust need a module or crate of their own anyway |
| JVM: one shared Gradle build with a source set per project (K4 route a) | As fast as a build per folder, but each new project costs 1 to 1.8 s once and invalidates the configuration cache of every JVM build, VS Code folds every project into one Eclipse project so packages clash, and Kotlin tests cannot see `internal` declarations |
| JVM: `javac` and `kotlinc` called directly (K4 route c) | Kotlin takes 2.6 to 4.7 s per run: a cold compiler every time, with no incremental compile |
| JVM: prefetch JUnit with a resolvable configuration in the workspace build | Misses `apiguardian-api`, which only JUnit's compile variant brings; building a real project from the template caches exactly what a folder needs |
| A venv or `node_modules` per project | Every start would need the network (NFR-6), and disk use multiplies |
| Run the native tool and parse its report (JUnit XML) | Less code per language, but loses the per-test hang guard, crash restart, output capture and debug launch the runner already has |
| Vitest or Jest for TypeScript | They need a network install and a transform of their own; `node:test` ships with Node 24 and runs `.ts` through type stripping |
| unittest for Python | Nothing to install, but pytest is what Python projects use and its failure messages are clearer; the cost is one dev dependency in the shared venv |
| Convert 0187 and 0248 into project problems | Loses their six-language single-file versions |
