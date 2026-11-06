# coding-study documentation

coding-study is a local, IDE-first study tool for software engineers: original problems stored as data, solved in your own editor in Python, TypeScript, Java, Kotlin, Go or Rust, and driven by a CLI (`cstudy`) that tests, benchmarks, explains and schedules reviews, in the terminal or through the local page `cstudy serve` serves. To install it and start practicing, read the [README](../README.md); to change it, read [CONTRIBUTING](../CONTRIBUTING.md).

## Reading order

1. [PRD](prd.md): why, for whom, requirements, success metrics, risks, open questions.
2. [Architecture](architecture.md): components, hexagonal boundaries, data flows, repository layout, toolchain.
3. Specs, in the order an implementer needs them (below).
4. [Roadmap](roadmap.md): phases and exit criteria.
5. [Decisions](#decisions): the ADRs behind the major choices.

## Specs

| Spec | Defines | Read when |
|------|---------|-----------|
| [problem-format](specs/problem-format.md) | `meta.yaml`, `tests.json`, type DSL and per-language mapping, serialization, comparators, design, progressive, project and concurrent formats, worked examples | Building codegen, runners, verify, or writing content |
| [runners](specs/runners.md) | CLI-runner protocol (test and bench modes), exit codes, hang guard, code location, project and suite jobs, stub generation, reference materialization | Building a runner or the runner adapter |
| [cli](specs/cli.md) | Every command, flag, output example, exit code; the config file | Building commands |
| [progress-and-scheduling](specs/progress-and-scheduling.md) | SQLite schema, grades, SM-2 variant, weakness score, `cstudy next` | Building progress features |
| [performance-analysis](specs/performance-analysis.md) | Optional time limits, size ladder, measurement, complexity classification, verdicts and confidence | Building `cstudy bench` or time limits |
| [content](specs/content.md) | Tracks, pattern taxonomy and targets, batches, non-autograded items, copyright policy | Planning content |
| [catalog](specs/catalog.md) | Binding manifest of every item: ids, slugs, titles, patterns, difficulty, kind, batch, owner stream | Writing content in a stream, or adding to the catalog |
| [service-projects](specs/service-projects.md) | Planned, not built: problems that run a real app in a Docker sandbox with lifecycle commands, built-in mock servers, backing services, HTTP grading and a dependency list shown before starting | Working on ADR 0019's phases |
| [versioning](specs/versioning.md) | Commit types and version bumps, the version workflow, `CHANGELOG.md`, `cstudy --version`, the GitHub release and the Homebrew tap | Committing, or changing how releases are versioned or published |
| [authoring](specs/authoring.md) | Authoring workflow, `problem.md` and `explanation.md` formats, ready criteria, every `cstudy verify` check | Writing or reviewing a problem |
| [web-ui](specs/web-ui.md) | `cstudy serve`: the local page, its API v1, runs and jobs as server-sent events, the security model, file API rules, code intelligence sessions with language servers, page behaviour, mocks, solutions, preferences and assets | Building or changing the web UI |
| [installation-and-workspaces](specs/installation-and-workspaces.md) | Packaging, content and workspace resolution, `cstudy init`, the runner runtime, project folders, IDE files, your own problems | Installing `cstudy`, setting up a workspace, or changing where files live |

## Guides

| Guide | Covers | Read when |
|-------|--------|-----------|
| [toolchains](guides/toolchains.md) | Installing and checking uv and Python 3.13, Node.js and pnpm, and a JDK 21 to 26 on macOS and Linux | Setting up a machine, or when `cstudy doctor` reports a missing toolchain |
| [web-ui](guides/web-ui.md) | `cstudy serve`: starting it, the views, editing and runs, project files, hints, solutions and mocks, preferences, code intelligence and autocomplete (live errors, hover, go to definition, completion), the keyboard, troubleshooting and security | Practising in the browser, or turning the editor's help on or off |

## Decisions

| ADR | Decision |
|-----|----------|
| [0001](decisions/0001-data-driven-tests.md) | Tests are language-neutral data; runners invoke, the CLI compares |
| [0002](decisions/0002-python-uv-cli.md) | The CLI is Python 3.13 managed with uv |
| [0003](decisions/0003-gradle-wrapper-jvm.md) | Java and Kotlin build with a committed Gradle wrapper |
| [0004](decisions/0004-original-problem-wording.md) | All problem text and tests are original |
| [0005](decisions/0005-empirical-complexity-analysis.md) | Optimality is judged empirically against a reference ladder, with stated confidence |
| [0006](decisions/0006-concurrency-stress-testing.md) | Concurrency problems are stress-tested against invariants over many runs, and broken references prove each scenario catches its bugs |
| [0007](decisions/0007-no-persistent-jvm-runner.md) | No persistent JVM runner in v1: the warm Java and Kotlin `cstudy test` meets NFR-1 through the Gradle daemon and a fresh JVM |
| [0008](decisions/0008-installable-tool-and-separate-workspaces.md) | `cstudy` is installed with its content bundled, and you practice in a separate workspace created by `cstudy init` |
| [0009](decisions/0009-ladder-calibration.md) | The ladder check tolerates drift and fixed costs, needs super-polynomial evidence for exponential growth, and treats sublinear classes as one band |
| [0010](decisions/0010-ide-integration.md) | Workspaces ship VS Code and IntelliJ project files that run `cstudy` and attach debuggers to its runner; `cstudy` stays the judge |
| [0011](decisions/0011-decimal-and-date-types.md) | `decimal` and `date` are scalar types with string wire forms; runners write decimals in canonical form so the comparators stay type-blind |
| [0012](decisions/0012-go-and-rust.md) | Go and Rust are required of every problem, after a per-problem backfill; compiled runners, exhaustive language dispatch |
| [0013](decisions/0013-homebrew-distribution.md) | Each release attaches the wheel and a hashed requirements file to a GitHub release, and the workflow points the `cstudy` formula in `bkuberek/homebrew-tap` at them |
| [0014](decisions/0014-project-problems.md) | Project problems are seeded folders in one language, solved in levels: native tests generated from `tests.json` for feedback, `cstudy submit` grades and opens levels |
| [0015](decisions/0015-local-web-ui.md) | A local web UI, `cstudy serve`, with full practice parity: every action calls the CLI's use case or runs its command, and runs stream live for every kind |
| [0016](decisions/0016-jdk-range.md) | Java and Kotlin run on JDK 21 to 26, within the range each problem declares |
| [0017](decisions/0017-async-project-problems.md) | Project problems grade asynchronous code on a virtual clock and concurrent code under stress: `async` methods, harness operations, stress cases with broken overlays, and Go 1.25 |
| [0018](decisions/0018-editor-code-intelligence.md) | The page's editor gets code intelligence from local language servers behind a setting, and completion behind a second one: live diagnostics, hover documentation and go to definition over one WebSocket per tab and root |
| [0019](decisions/0019-service-projects.md) | Planned, not built: service projects always run in a Docker sandbox, a real app against mock servers and optional backing services, graded over HTTP |
| [0020](decisions/0020-catalog-labels.md) | Problems and items have three independent labels, domain, role and scope, with filters in `cstudy list`, `cstudy next` and the Problems view; the first seven security and AI/LLM problems, in Python and TypeScript |
| [0021](decisions/0021-ai-reviewed-problems.md) | Planned, not built: an opt-in class of problems reviewed by a live LLM with your own key; "works on your own machine" replaces "works offline" |
| [0022](decisions/0022-settings-and-reset.md) | The Settings view edits the whole `config.toml` with tomlkit, keeping the user's comments, from a description of each key held by the parser |

## Conventions

- Lowercase hyphenated filenames; GitHub-flavored Markdown.
- Specs are normative: an implementation that disagrees with a spec is a bug in one of them, fixed in the same change.
- Unsettled items live in [PRD open questions](prd.md#8-open-questions) with the default the specs assume.
