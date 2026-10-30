# ADR 0014: Project problems are seeded folders in one language, solved in levels

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-30 |
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
- **`tests.json` stays the single source.** Its cases feed the statement's examples, the visible native tests and the grade. `cstudy` generates one native test file per level from that level's visible cases (pytest, `node:test`), at start for level 1 and at each unlock for the next level, and never rewrites one. Authors may ship extra test files in the starter, and users add their own.
- **Two commands.** `cstudy test` runs the native suite: the generated files, the starter's and your own. It is feedback only, never a grade, and opens nothing. `cstudy submit` sends every case of the unlocked levels, visible and hidden, through the runner protocol; the core's comparator judges each output, and a submission that passes every one opens the next level. Editing a generated test file never changes a grade.
- **Levels stay hidden until they open.** The starter holds only level 1's methods. Each unlock reveals the next statement section, which names the methods to add, and the grader checks only the methods of the levels it grades.
- **Hidden cases.** A failing hidden case shows its input, expected and actual in a practice attempt, and only a count in a mock attempt.
- **Grade.** `cstudy done` takes a rating once level 1 passes and caps the grade by the levels finished: all levels, no cap; all but the last, `hard`; fewer, `again`. The time box stays soft: finishing over it caps the grade at `hard`, as today.
- **One final reference.** Each project problem has exactly one approach, whose reference is an overlay on the starter (`solutions/<approach>/`, changed and added files only) implementing every level. No snapshot per level.
- **Runners host the framework.** The Python and TypeScript runners learn to load a project folder for grading and to run the native framework in-process as a new `suite` job, so a test gets the runner's hang guard, output capture, crash restart and debug launch.
- **Shared toolchains.** A project folder reaches the workspace's Python venv and Node installs by relative path; nothing is installed per project, so a project starts offline (NFR-6).
- **Python and TypeScript first.** Java, Kotlin, Go and Rust project problems are not yet supported, and `cstudy verify` rejects one. Each needs a build of its own per project (a Gradle build, a Go module, a Cargo crate) and a spike before it is specified:

  | Language | Open question | Spike |
  |----------|---------------|-------|
  | Java, Kotlin | Warm p50 of compiling main and test sources plus a JUnit Platform launch against NFR-1's 3 s and 5 s; JUnit resolved offline; locks and per-run class copies per project build. The Gradle step already takes 0.85 to 1.55 s warm for one package, and ADR 0007 names multi-file problems as its revisit trigger | K4 |
  | Go | One module per project in the root `go.work` for gopls; the overlay registration inside a project package | K5 |
  | Rust | `cargo test` results on stable Rust without libtest's JSON output; two profiles (tests in dev, grading in release) compiled per change; a harness that depends on the project crate by path | K6 |

## Consequences

- A project problem has no generated stub, no generator, no bench, no oracle and no time limit: `cstudy bench`, `cstudy test --perf`, `--stress` and `--time-limit`, and `cstudy verify --oracle` and `--ladder`, do not apply to it.
- Coverage lines and `--lang` filters count a project only in its language. The catalog grows one problem per language version, and each version costs a full authoring pass; the TypeScript pilot measures that cost.
- New CLI surface: `cstudy submit` and `cstudy status`, a `projects/` folder in every workspace, pytest in the workspace's Python template, `submissions` and `level_unlocks` tables, and verify checks S14 to S16 and D9.
- The Python runner gains a package-aware loader that compiles project modules from source on every run and keeps library bytecode under `.cs/pycache/`, and one runner process per project job, since two projects may both define a top-level `bank` module.
- A starter's `pyproject.toml` holds tool tables only. A `[project]` table, `requires-python` or `[tool.uv]` in it could make `uv run` delete the shared venv, so check S15 rejects them.
- The pilots are `0249-bank-project-python`, then `0250-bank-project-typescript`, with the behavior of `0248-scheduled-transfers-bank`. 0187 and 0248 stay progressive, since converting them would remove their six-language versions.
- The web interface is still a PRD non-goal; the project folder, `cstudy submit --json` and `cstudy status --json` are the boundary it would build on.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| Spikes K4, K5 or K6 report | Specify that language's project folder, suite and grading, amending this ADR; K4 may also reopen [ADR 0007](0007-no-persistent-jvm-runner.md) |
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
| A venv or `node_modules` per project | Every start would need the network (NFR-6), and disk use multiplies |
| Run the native tool and parse its report (JUnit XML) | Less code per language, but loses the per-test hang guard, crash restart, output capture and debug launch the runner already has |
| Vitest or Jest for TypeScript | They need a network install and a transform of their own; `node:test` ships with Node 24 and runs `.ts` through type stripping |
| unittest for Python | Nothing to install, but pytest is what Python projects use and its failure messages are clearer; the cost is one dev dependency in the shared venv |
| Convert 0187 and 0248 into project problems | Loses their six-language single-file versions |
