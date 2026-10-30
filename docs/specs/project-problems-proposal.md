# Proposal: Project problems

A **project problem** is a folder of seeded files in one language. You edit those files or add new ones, `cstudy` builds and tests the whole folder, and the problem opens in levels that build on the same code, the way timed multi-level practical exercises are usually run. This page scopes the format, the runners, the CLI and the checks, recommends a design, and lists what the owner still has to decide. Nothing here is implemented.

| Field | Value |
|-------|-------|
| Status | Proposed. Not normative: until it is accepted, the other specs describe what `cstudy` does |
| Date | 2026-10-30 |
| On acceptance | The decisions become ADR 0014, the specs below are amended in the same change, and this page is removed |
| Specs affected | [problem-format](problem-format.md), [runners](runners.md), [cli](cli.md), [authoring](authoring.md), [installation-and-workspaces](installation-and-workspaces.md), [progress-and-scheduling](progress-and-scheduling.md), [catalog](catalog.md), the [PRD](../prd.md) |
| Builds on | ADR [0001](../decisions/0001-data-driven-tests.md), [0007](../decisions/0007-no-persistent-jvm-runner.md), [0008](../decisions/0008-installable-tool-and-separate-workspaces.md), [0010](../decisions/0010-ide-integration.md), [0012](../decisions/0012-go-and-rust.md) |

This is a proposal page rather than ADR 0014 because the decision log holds decisions only: all 13 ADRs were committed with status Accepted, none was ever Proposed (`git log -S Proposed -- docs/decisions` finds nothing), and unsettled items stay out of it (`docs/README.md:56`). Six owner decisions (O1 to O6) are still open.

## Summary

A new `kind: project` on the `practical` track reuses the progressive kind's levels, statement rendering and unlocking, but the user's code is a folder: `cstudy start` copies the problem's `starter/` tree to `projects/<slug>/` in the workspace, and every level adds to the same code. A project problem has exactly one language. Its cases stay in `tests.json`, the single source for the statement's examples, for the native visible tests that `cstudy` generates per level (pytest, `node:test`) and for grading. `cstudy test` runs the native suite as feedback; `cstudy submit` grades every case of the unlocked levels through the existing runner protocol, judged by the core's `ops` comparator, and opens the next level on a full pass. The Python and TypeScript runners learn to load a folder and to host their native test framework in-process, so a test gets the hang guard, output capture and debugger the runner already provides. JVM, Go and Rust follow after spikes.

| Area | Recommendation |
|------|----------------|
| Kind | New `kind: project`, track `practical`, levels as in `progressive` |
| Language | Exactly one per problem; another language is another problem, linked through `related` |
| Content | `starter/` (the seeded tree), `tests.json` (every case, with levels), `solutions/<approach>/` (the reference as an overlay on the starter) |
| Workspace | `projects/<slug>/`, one self-contained folder per started project, sharing the toolchain installs of `python/` and `typescript/` |
| Visible tests | Native files generated from each level's visible cases at start and at each unlock; yours to edit and extend |
| Grading | `cstudy submit`: every case of the unlocked levels through the runner, judged by the core |
| Pilots | `bank-project-python`, then `bank-project-typescript`, on the behavior of `0248-scheduled-transfers-bank` |

## Context

| Fact today | Evidence |
|------------|----------|
| A progressive problem is one class whose API grows over levels; a run that passes every case of the unlocked levels opens the next one | `problem-format.md:399-428`, `cli/src/coding_study/application/run_tests.py:301-311` |
| User code is one file per problem and language, inside a shared project per language | `cli/src/coding_study/domain/layout.py:101-157`, `architecture.md:191-200` |
| The Python runner executes one file as a module named `cs_target_<n>`, so a package-relative import in a second file fails | `runners/python/src/cs_runner/loading.py:38-55`; spike: `ImportError: attempted relative import with no known parent package` |
| The TypeScript runner imports the target by file URL, so relative `.ts` imports already resolve | `runners/typescript/lib/execute.ts:188-193` |
| Java, Kotlin and Go already compile every file of the problem's package directory | `runners.md:33`, `cli.md:37` |
| Both script runners check every declared method when a job loads | `loading.py:66-74`, `execute.ts:218` |
| Tests are language-neutral data; per-language test files were rejected for their authoring cost and drift | `../decisions/0001-data-driven-tests.md:15-18,31-32` |
| IDE-native test configurations were rejected as a second judge: `cstudy` stays the judge | `../decisions/0010-ide-integration.md:22,43` |
| A catalog problem lists every language that can express it, with three exceptions | `../decisions/0012-go-and-rust.md:40-47`, `cli/src/coding_study/domain/static_checks.py:207-212` |
| The PRD lists a web UI as a non-goal, and user code runs without a sandbox | `../prd.md:60,116` |

## Owner decisions already made

- **One language per project problem.** `meta.yaml` names one language, and the starter tree, tests and reference exist only in it. This is a deliberate exception to the six-language rule of ADR 0012, as workspace problems already are.
- **A version in another language is a separate problem**, built again from scratch: its own id, folder, starter tree, tests and reference. The statement wording can be reused; nothing else is shared or inherited, and there are no variants inside a problem. Siblings point to each other through `related`.
- **The pilots are Python, then TypeScript**: two banking project problems.

## 1. On-disk format

### Content tree

```text
problems/0249-bank-project-python/
  meta.yaml             # kind: project, languages: [python], levels, the graded API, the project block
  problem.md            # "## Level <n>: <title>" sections as for progressive problems, plus "## Project"
  tests.json            # every case with its level, as for progressive problems
  starter/              # the seeded tree; cstudy start copies it to <workspace>/projects/<slug>/
    README.md           # the contract (entry class and module) and how to run the tests
    pyproject.toml      # tool settings only: pytest, pyright, ruff
    bank/__init__.py
    bank/bank.py        # the entry class Bank
    bank/models.py      # seeded model types
    tests/conftest.py   # optional fixtures from the author
  solutions/
    explanation.md      # one section per approach, as today, plus "### Design"
    reference/          # approach `reference`: an overlay on starter/, changed and added files only
      bank/bank.py
      bank/ledger.py
```

The TypeScript pilot has the same shape, with `package.json`, `tsconfig.json`, `src/bank.ts`, `src/models.ts` and `tests/`.

| Item | Rule |
|------|------|
| Starter | Every file the user starts with, in the project's own layout. Text files only; no build output, caches or dependency lock files; at most 50 files and 256 KiB (S15) |
| Entry | The class the grader constructs. Python: a dotted module (`bank.bank`); TypeScript: a file (`src/bank.ts`) exporting the class by name. `README.md` and `## Project` say it must stay there. A starter may also declare the API as an interface the entry class implements (an `abc.ABC` subclass, a TypeScript `interface`); the grader needs only the class, and whether the interface shows every level's methods is O3 |
| Build files | The project's own `pyproject.toml`, or `package.json` and `tsconfig.json`. They reach the workspace's shared installs by relative path; nothing is installed per project |
| Visible tests | Not stored in the content: generated from `tests.json` ([Tests](#2-tests)) |
| Hidden tests | The hidden cases of `tests.json` |
| Reference | One final reference per approach in `solutions/<approach-id>/`, an overlay: `cstudy verify` copies `starter/`, then the overlay, into `.cs/build/projects/<slug>/<approach>/` and runs that. It implements every level, as progressive references do (`authoring.md:215`). Snapshots per level are O6 |
| Explanation | `solutions/explanation.md` as today, with a `### Design` subsection per approach: the files and what each is responsible for |

### meta.yaml

```yaml
# yaml-language-server: $schema=../../schemas/meta.schema.json
id: "0249"
slug: bank-project-python
title: Bank Project (Python)
status: draft
difficulty: hard
track: practical
kind: project
languages: [python]
levels:
  - {level: 1, title: Accounts and transfers}
  - {level: 2, title: Top spenders}
  - {level: 3, title: Scheduled transfers}
  - {level: 4, title: Merges and balance history}
signature:              # the API the grader calls: canonical names, a level on every method, format unchanged
  class:
    name: Bank
    constructor: {params: []}
    methods:
      - {name: createAccount, level: 1, params: [{name: timestamp, type: long}, {name: accountId, type: string}], returns: {type: bool}}
comparator: {type: ops}
project:
  entry: bank.bank      # Python: dotted module; TypeScript: src/bank.ts
  tests: tests          # where cstudy writes the generated level tests; default "tests"
approaches:
  - {id: reference, name: Accounts with balance histories and a due-time heap, role: optimal, time: "...", space: "...", time_class: "n log n", space_class: "n"}
related: [bank-project-typescript, scheduled-transfers-bank]
estimate_minutes: 90
```

| Change | Detail |
|--------|--------|
| Schema | `kind` gains `project` (`schemas/meta.schema.json:22`); `levels` is required for `progressive` and `project` (today only `progressive`, `:102-105`); a `project` object (`entry` required, `tests` optional) is required for `project` and forbidden otherwise; `languages` holds exactly one item for `project` |
| Domain | `ProblemKind.PROJECT` and a `project` value on `ProblemMeta`. Level code accepts both kinds through one helper; `levels.py:98` accepts `PROGRESSIVE` only today |
| Slugs | Carry the language (`bank-project-python`, `bank-project-typescript`): a slug is unique and is the key in `progress.db` (`problem-format.md:41`), so siblings cannot share one |
| Sibling link | `related` only. No dedicated field: `cstudy list --lang` already filters by language, and nothing needs more. An optional `variant_of` becomes worth adding only if `cstudy start bank-project --lang typescript` is wanted later |
| `tests.json` | Unchanged: op sequences with `level`, literal `expected`, `visible`, `note`. Statement examples keep their `<!-- case: id -->` markers, and for a project problem the rendered op names use the problem's language (`create_account` in Python); `domain/statement.py:175` prints canonical names today |

## 2. Tests

One language removes the parity argument for language-neutral data, and since each language version is built from scratch, cases are not reused across versions either. The other reasons for `tests.json` remain: grading outside code the user can edit, the statement's examples coming from the same cases as the tests, and one level and judging machinery shared with progressive problems. Weighed again with that in mind:

| Option | Realism | Sources of truth | Cost | Verdict |
|--------|---------|------------------|------|---------|
| A. Hand-written native files, visible and hidden | Highest | Two: test code, and examples written into the statement by hand | Per problem: every test in code. Per language: grading from framework results, and hidden tests that must compile against whatever the user wrote | Rejected for grading: the verdict comes from a framework over user-editable code, the second judge ADR 0010 rejected (`0010:43`) |
| B. `tests.json` only | Lowest: nothing to run with the language's own tools | One | Lowest | Rejected: misses the realism goal |
| C. `tests.json` for grading, hand-written native visible tests in `starter/` | High | Two: each example exists as a case and as code; verify proves both pass the reference, but not that they agree | Per problem: every visible case written twice, as data and as test code | Viable fallback |
| D. `tests.json` for everything; native visible tests generated from it | High: real pytest or `node:test` files, one test per visible case, run natively and edited freely | One | Per language, once: a generator of about 200 lines that reuses the naming rules and value rendering the stub generators have | **Recommended** |

Recommendation: **D**, plus two additions. Your own test files in `tests/` run together with the generated ones, and an author may ship extra hand-written test files in `starter/` (fixtures, a sample test), which `cstudy verify` runs against the reference (D9). O2 asks the owner to confirm generated over hand-written visible tests.

Generated level 1 tests for the pilots, from case `ex1` of 0248:

```python
"""Level 1 examples of bank-project-python, written by `cstudy start`.

Yours to edit and extend: cstudy never rewrites this file.
"""

from bank.bank import Bank


def test_ex1() -> None:
    bank = Bank()
    assert bank.create_account(1, "ivy") is True
    assert bank.create_account(2, "leo") is True
    assert bank.create_account(3, "ivy") is False
    assert bank.deposit(4, "ivy", 800) == 800
    assert bank.deposit(5, "max", 50) == -1
```

```ts
// Level 1 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Bank } from "../src/bank.ts";

test("ex1", () => {
  const bank = new Bank();
  assert.equal(bank.createAccount(1, "ivy"), true);
  assert.equal(bank.createAccount(2, "leo"), true);
  assert.equal(bank.createAccount(3, "ivy"), false);
  assert.equal(bank.deposit(4, "ivy", 800), 800);
});
```

| Rule | Detail |
|------|--------|
| Comparators | Generated assertions follow the problem's comparator: `exact` compares type-strictly, so booleans use `is True` in Python, as the core never equates `true` and `1` (`problem-format.md:354`); `unordered` sorts both sides; `float` uses `pytest.approx` or a tolerance helper. `checker` is not allowed for project problems (S14) |
| Files | One file per level, `tests/test_level_<n>.py` or `tests/level-<n>.test.ts`, written at start (level 1) and at each unlock, never over an existing file |
| Expected values | Literal in `tests.json`, and `cstudy verify` requires the reference to return every one of them (D3): no expected value the reference disagrees with can ship. This is how hand-written cases work today; computed values exist for `generate` cases only (`problem-format.md:345`). ADR 0001 decides that tests are data and that the core judges by behavior (`0001:15-18`); keeping the values literal also keeps the author's reading of the statement as an independent check on the reference |
| Hidden grading | `cstudy submit` sends the inputs of every case of the unlocked levels, visible and hidden, to the runner, which constructs the entry class and calls the operations; the core's `ops` comparator judges each output, with the per-case hang guard and the report rules of today. Visible cases are graded from `tests.json` too, so editing the generated files never changes a grade |

## 3. Runner scoping

### Workspace layout

| Today | With project problems |
|-------|-----------------------|
| `python/`, `typescript/`, `jvm/`, `go/` and `rust/` hold every started problem as one file (`installation-and-workspaces.md:63-84`) | Unchanged, plus `projects/<slug>/`: one self-contained folder per started project, tracked like practice files |
| Toolchains are installed once per language project (`python/.venv`, `typescript/node_modules`) | Shared: a project reaches them by relative path, so a project starts offline (NFR-6, `../prd.md:101`) and nothing is installed per project |
| `--fresh` archives one file to `.archive/<slug>/<attempt_id>-<lang>/` (`start_attempt.py:172-175`) | Archives the whole folder there |
| `cstudy test --watch` watches a file or a package directory (`layout.py:136-145`) | Watches the folder, ignoring caches and `.venv` |
| `test_runs.code_hash` hashes the watched path (`run_tests.py:317-322`) | Hashes the folder's files, ignoring caches |
| The workspace `.gitignore` ignores `.venv/` and caches | Adds `projects/*/.venv`: the Python link below is a symlink, which a pattern with a trailing slash does not match |

A top-level `projects/` rather than `python/projects/`: the folder is the unit the owner described, it opens as its own editor root, it is the boundary the web UI's file API needs, and the JVM, Go and Rust versions need build files of their own anyway (a Gradle build, a module, a crate). The cost is a little editor configuration in each starter, pointing at the shared installs.

### Python

| Concern | Design |
|---------|--------|
| Interpreter | The workspace venv, `python/.venv/bin/python`, as today (`adapters/languages/python/runner.py:94-102`). `cstudy start` links `projects/<slug>/.venv` to `../../python/.venv`, so editors, `.venv/bin/pytest` and `source .venv/bin/activate` work in the folder |
| pytest | Added to the dev group of the workspace template (`workspace_template/python/pyproject.toml:11-15` lists debugpy, pyright and ruff). An older workspace gets a doctor WARN with `fix: uv add --dev pytest --directory python`, as debugpy does (`application/doctor.py:525-531`). `cs_runner` imports pytest only for a suite job, so file problems never need it |
| Project config | `pyproject.toml` with tool tables only: `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`), `[tool.pyright]` (`venvPath = "."`, `venv = ".venv"`), `[tool.ruff]`. No `[project]` table, so no second venv or lock file per project (K1) |
| Import path | The runner starts in the project root, imports its own modules, then puts the root on `sys.path` and imports the entry by its dotted name. `from .models import Account` and `from bank.models import Account` both work |
| Fresh code | Modules under the project root compile from source on every run, as `_SourceOnlyLoader` does for single files (`loading.py:30-35`), so an edit made within the same second is never hidden by stale bytecode. Library bytecode goes to a persistent `PYTHONPYCACHEPREFIX` under `.cs/pycache/`, so nothing is written into the project and pytest stays warm |
| Isolation | One runner process per project job. Two projects that both define a top-level `bank` cannot share an interpreter's `sys.modules`, so `cstudy verify` never batches projects into one process as it batches files |
| Grading job | A class job with a new target `{"project": "<abs root>", "module": "bank.bank"}` and a signature cut to the methods of the levels it grades, since the loader checks every declared method (`loading.py:72-73`) |
| Native suite | A new `suite` job: the runner calls `pytest.main(...)` in-process with `-p no:cacheprovider`, plugin autoloading off (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) and a small plugin that writes `case_start` and `case_result` per test (node id, outcome, duration, failure message, captured output) to the event file |
| Hangs and crashes | Unchanged rules: the watchdog sees one event pair per test, kills the process group on a hang, and restarts the suite with the reported tests deselected (K2) |
| Debug | Unchanged launch (`python/runner.py:79-92`): debugpy wraps `-m cs_runner`, which hosts pytest in the same process, so breakpoints in the code and in the tests both stop |

### TypeScript

| Concern | Design |
|---------|--------|
| Runtime | Node 24 type stripping, as today; nothing is built. Starter and reference code use erasable syntax only: in the spike, a parameter property failed with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`. Node refuses such a file when it loads, so D1 and D3 catch it, and `--typecheck` reports it earlier through `erasableSyntaxOnly` |
| Module format | The project's `package.json` declares `"type": "module"`, so every `.ts` file is ESM, and imports name files with their extension (`../src/bank.ts`) |
| Resolution | Relative imports resolve from each file's URL. A bare import resolves only to Node's builtins: the project has no `node_modules`, and `#support` is not mapped, since the import map lives in `typescript/package.json` and a package's import map cannot point outside the package. The pilots use no node types and no `decimal` (S14); a later starter can add them with its own `support.ts` that re-exports the runtime's support module, as `typescript/support.ts` does |
| Editor types | `tsconfig.json` as the workspace's (`nodenext`, `noEmit`, `allowImportingTsExtensions`, `erasableSyntaxOnly`, `verbatimModuleSyntax`, `strict`), with `typeRoots: ["../../typescript/node_modules/@types"]` so `node:test` and `node:assert` have types; VS Code already points at the workspace's TypeScript (K3) |
| Grading job | The existing `{"path": <abs entry file>}` target (`domain/runs.py:37-41`), launched in the project root instead of `typescript/` (`adapters/languages/typescript/runner.py:117-124`), with the signature cut by level as in Python (`execute.ts:218`) |
| Native suite | `node:test` with `node:assert/strict`: part of Node, so no dependency and no network. The `suite` job calls `run({ files, isolation: "none", concurrency: 1 })` and turns `test:start`, `test:pass` and `test:fail` into protocol events, keeping the assertion's `expected` and `actual` |
| Type check | `cstudy test --typecheck` runs the workspace's `tsc --noEmit -p projects/<slug>` and keeps the project's diagnostics; today it filters to one file (`typescript/runner.py:134-142`) |
| Debug | `--inspect-wait` as today (`typescript/runner.py:154-159`); with `isolation: "none"` the tests run in the inspected process (K2) |
| Native command | `node --test` (or `npm test`) in the folder, offline and without `cstudy` |

### Spike evidence

A disposable spike in the scratchpad (nothing committed) built a two-file bank in each language with two tests, one failing on purpose, on Node 24.18.0 and pytest 9.1.1.

| Question | Result |
|----------|--------|
| Can today's Python loader import a module with a package-relative import? | No: `ImportError: attempted relative import with no known parent package` |
| Does pytest run in-process from outside the project and report per test? | Yes: `case_start` and `case_result` per test from a plugin, with pytest's assertion detail (`assert -1 == 5 ... where -1 = deposit(1, 'max', 5)`), and no `__pycache__` written into the project under `PYTHONPYCACHEPREFIX` |
| Does `node --test` find `.ts` tests without configuration? | Yes: it discovered `tests/level-1.test.ts`, and relative `.ts` imports resolved |
| Does `node:test` run in-process and report per test? | Yes: `run({ isolation: "none" })` from a host script outside the project reported `test:start`, `test:pass` and `test:fail` with `expected: 5` and `actual: -1` |
| Hosted run time, median of 5, runner side only (1-minute load 3.7) | pytest 0.12 s with a warm bytecode prefix and 0.54 s with a cold one (1.25 s cold with an extra pytest plugin installed); `node:test` 0.06 s |

### JVM, Go and Rust (later phases)

| Language | Folder | Visible suite | Grading | Known risks |
|----------|--------|---------------|---------|-------------|
| Java, Kotlin | A Gradle build of its own (`settings.gradle.kts`, `src/main`, `src/test`) run with the workspace's wrapper and daemon, including `../../.cs/runtime/runners/jvm` | JUnit 5 (Kotlin: kotlin.test on JUnit 5), compiled by Gradle (`testClasses`) and launched by the JVM runner through the JUnit Platform Launcher API, which skips Gradle's forked test JVM | `ClassTarget` on the project's main classes, as today | The Gradle step is already 0.85 to 1.55 s warm for one package (`0007:20-23`), and a test source set adds to it; ADR 0007 names multi-file problems as its revisit trigger (`0007:28`). JUnit jars must be resolved by `doctor --fix` to stay offline. The locks and per-run class copies (`runners.md:39-41`) extend to builds per project |
| Go | A module (`go.mod`, `module <snake_slug>`); `cstudy start` adds `use ./projects/<slug>` to the root `go.work`, as it adds Rust examples to `rust/Cargo.toml` today (`start_attempt.py:88-97`) | Generated `level<n>_test.go`; `go test -json` gives events per test | The build's `go.work` adds the module, and the registration enters the entry package through `-overlay` as today (`runners.md:53`) | Low: a warm rebuild took 0.16 s (`0012:18`). gopls with one module per project |
| Rust | A library crate (`Cargo.toml`, `src/lib.rs`, modules) with `.cargo/config.toml` pointing crates.io at the runtime's vendored crates, as `rust/` does (`installation-and-workspaces.md:107`) | Generated `tests/level_<n>.rs`; `cargo test --offline`. libtest's JSON output needs a nightly flag, so results come from the plain format or a generated harness | The harness package depends on the project crate by path, instead of including one file as a `#[path]` module (`runners.md:69`), so the crate's module tree compiles as written | Tests (dev profile) and grading (release profile) compile the crate twice per change; the shared target directory's lock serializes runs; dependencies are limited to the vendored crates (S15) |

### Protocol additions

| Addition | Detail |
|----------|--------|
| Target | `{"project": "<abs root>", "module": "<dotted>"}` for Python; TypeScript keeps `{"path": ...}` |
| Launch | `RunnerLaunch.cwd` is the project root for project jobs |
| Job kind `suite` | `{"job_id": "<slug>/suite", "kind": "suite", "framework": "pytest", "root": "<abs root>", "paths": ["tests"], "skip": []}`, with `"node-test"` for TypeScript. The framework discovers the tests, so the request lists no cases; `case_result` carries `status` `ok`, `failed` or `skipped`, a `message`, and `expected` and `actual` when the framework reports them |
| Capability | `hello.features` gains `suite` and `project`; the field exists (`domain/runs.py:266-274`) |
| Judging | A suite result is the framework's verdict on code the user may edit. It is feedback, never a grade: no comparator runs on it and no level opens from it. Grades come only from `tests.json` cases, judged in the core (`architecture.md:3`) |

### Cost per run

| Language | `cstudy test` (native suite) | `cstudy submit` (grading) | Basis |
|----------|------------------------------|---------------------------|-------|
| Python | About 0.12 s in the runner, plus the CLI's own start | As a `cstudy test` today: 0.47 to 0.65 s warm in total | Spike; `0007:18` |
| TypeScript | About 0.06 s in the runner, plus the CLI's own start | As today: 0.44 to 0.46 s warm in total | Spike; `0007:19` |
| Java, Kotlin | Unknown: at least the Gradle step for two source sets | The Gradle step plus a fresh JVM | K4 |
| Go | Inferred under 1 s warm | Inferred under 1 s warm | `0012:18` |
| Rust | Inferred 1 to 3 s warm, two profiles | Inferred under 1 s after a test build | `0012:18`, K6 |

Python and TypeScript stay within NFR-1's 1.0 s (`../prd.md:96`) with room to spare; the phase 1 and 2 exit checks measure it.

## 4. Levels as stages

| Topic | Design |
|-------|--------|
| Carry-over | One folder for every level: level 2 extends the code of level 1. Nothing is reset or replaced when a level opens |
| Unlock | O1 decides the trigger. Recommended: a `cstudy submit` that passes every case, visible and hidden, of levels 1 to the unlocked level opens the next one, rewrites the statement (`application/statement_file.py`) and writes that level's test file. One submission opens at most one level, as today (`problem-format.md:426`) |
| At level N | Statement sections 1 to N, generated test files for levels 1 to N, and your code. Every submission grades levels 1 to N again, because later rules change earlier results: a scheduled transfer that runs counts toward top spenders |
| Locked levels | Their statement sections, test files and hidden cases stay hidden. Whether their methods appear in the starter is O3 |
| `--level N` | `cstudy test --level N` runs the generated files of levels 1 to N and your own tests; `cstudy submit --level N` grades levels 1 to N and opens nothing unless N is the unlocked level. N above the unlocked level exits 3, as today (`levels.py:45-58`) |
| Timer | `cstudy start --timer` as today; for a project, `--timer` without a value takes `estimate_minutes`. `cstudy status` shows the elapsed and remaining time, and each unlock records its time, so `status` and `stats` show the time per level. Soft or hard time box: O5 |
| Partial credit | Every submission stores a tally per level (passed of total, visible and hidden). `status` shows the best tally per level; how `cstudy done` grades from it is O5 |
| Data | `attempts.level_unlocked` as today (`progress-and-scheduling.md:32`); `stub_path` and `archive_path` hold the folder. New tables: `submissions` (attempt, time, code hash, tallies per level as JSON, duration) and `level_unlocks` (attempt, level, unlocked_at) |

## 5. CLI end to end

| Command | For a project problem |
|---------|-----------------------|
| `cstudy start <slug>` | The language is the problem's own: `--lang` may repeat it, another language exits 3 (`start_attempt.py:73-76`), and `default_lang` never applies. A new attempt copies `starter/` to `projects/<slug>/` without overwriting a file, links `.venv` (Python), writes the level 1 test file, renders the statement and opens `$EDITOR` on the folder and the statement. A resumed attempt writes back any missing generated file of an unlocked level, as a missing stub is written today (`start_attempt.py:79-85`). `--fresh` and review attempts archive the folder first |
| `cstudy test [<slug\|file>]` | Runs the native suite: the generated files of the unlocked levels and your own tests. Takes `--level`, `--case <test id>`, `--watch` (the folder), `--json`, `--debug` and, for TypeScript, `--typecheck`. Stored in `test_runs`; never opens a level |
| `cstudy submit [<slug\|file>]` (new) | Grades every case of the unlocked levels through the runner, stores a submission, and opens the next level on a full pass (O1). Takes `--level` and `--json`; no `--debug`: a failing hidden case shows its input (O4), which you can debug as a test of your own |
| `cstudy status [<slug\|file>]` (new) | Level, timer, last test run, best submission per level, files changed or added against the starter, next step; `--json` for IDEs and the web UI |
| Reset | No new command: `cstudy start --fresh` archives the folder and starts again at level 1. Restoring one file from the starter (`cstudy start --restore <path>`) comes with the starter manifest in phase 3 |
| `cstudy done` | As O5 decides; the latest submission plays the part the latest test run plays today (`cli.md:414-417`) |
| `cstudy hint`, `show`, `solution` | Unchanged; `solution` shows the explanation, then the reference as a diff against the starter |
| `cstudy ide` | The same tasks: any file inside `projects/<slug>/` becomes a solution file target (today only practice paths are, `cli.md:30-41`); VS Code excludes `projects/*/.venv` from watching and search |
| `cstudy next`, `list` | `--lang` filters projects by their language; `next --start` starts a project in its own language |
| `cstudy bench`, `test --perf`, `test --stress` | Exit 3: no generator and no ladder |
| `cstudy mock` | Leaves projects out until O5 is settled |
| `cstudy doctor` | WARN when pytest is missing from `python/.venv` or the workspace has no `projects/` (`--fix` writes it) |
| `cstudy verify` | [Authoring and verification](#6-authoring-and-verification) |

```text
$ cstudy start bank-project-python
bank-project-python · hard · practical · python · project
project    projects/bank-project-python (7 files)
entry      bank/bank.py: Bank
tests      tests/test_level_1.py (2 tests)
statement  .statements/bank-project-python.md
level      1 of 4: Accounts and transfers
next       cstudy test --watch, then cstudy submit
```

```text
$ cstudy test
bank-project-python · python · levels 1-2 of 4 · timer 31:40 / 90:00
suite  pytest, 0.3s

PASS     tests/test_level_1.py::test_ex1
PASS     tests/test_level_1.py::test_ex2
FAIL     tests/test_level_2.py::test_ex3
         assert ['dan(300)', 'eve(350)'] == ['eve(350)', 'dan(300)']
PASS     tests/test_overdraft.py::test_refuses_overdraft   yours

3/4 passed · total 0.7s
```

```text
$ cstudy submit
bank-project-python · python · submit levels 1-2 of 4 · timer 33:05 / 90:00

level 1  PASS     5/5 (2 visible, 3 hidden)
level 2  FAIL     4/5
FAIL     h3    hidden · level 2
         input     ops ["Bank", "create_account", ...]  args [[], [1, "zoe"], ...]
         expected  ["abe(60)", "zoe(60)", "mia(0)"]
         actual    ["zoe(60)", "abe(60)", "mia(0)"]

9/10 passed · level 3 opens when levels 1-2 pass
```

A full pass ends with `all passed · level 3 unlocked: Scheduled transfers · wrote tests/test_level_3.py · statement updated`.

```text
$ cstudy status
bank-project-python · python · project · attempt 41
level      2 of 4: Top spenders (level 2 opened at 18:02)
timer      33:05 / 90:00
tested     3/4 passed, 1 min ago
submitted  level 1 5/5 · level 2 4/5, 2 min ago
files      2 changed, 1 added against the starter
next       cstudy submit once level 2 passes
```

## 6. Authoring and verification

| Step | Action | Check |
|------|--------|-------|
| 1 | `cstudy new <slug> --from-template project-python` (or `project-typescript`): a starter with an entry class and one level | `cstudy verify <slug> --static` |
| 2 | Write `problem.md` (levels and `## Project`) and `tests.json` (at least 2 visible and 2 hidden cases per level) | `--static` |
| 3 | Shape the starter: the entry class, the seeded files, the README | `cstudy verify <slug>` (D1) |
| 4 | Write the reference overlay, level by level | `cstudy verify <slug>` (D3, D9) |
| 5 | Write `explanation.md` with `### Design`; set `status: ready` | `cstudy verify <slug> --require-ready` |

| Check | Rule |
|-------|------|
| S14 | `kind: project`: exactly one language; track `practical`; `project.entry` well formed for the language; comparator `ops` with `exact`, `unordered` or `float` per method, because generated tests cannot express a `checker`; signature types limited to scalars, arrays and lists: no node types, and no `decimal` in TypeScript, whose `Decimal` class comes from the runner's support module, until a starter carries its own `support.ts` |
| S15 | The starter exists and stays within its limits, holds no build output or caches, contains the entry file, has no top-level Python module named after a standard-library module, and (later) keeps Rust dependencies within the vendored crates. Overlay paths stay inside the tree, and every directory in `solutions/` is a declared approach |
| S16 | Generated test file names do not collide with starter files; `problem.md` has a `## Project` section |
| S5, S10 | As for progressive problems: level sections, contiguous levels, cases using only methods of their level or below |
| S13 | `must list` does not apply: the third exception, next to the subset tracks and workspace problems (`static_checks.py:211`); `cannot list` still does |
| D1 | The starter loads: the grading job finds the entry class and the level 1 methods (cases fail with errors, never `load_error`), and the native suite runs without crashing the runner |
| D3 | The reference passes every case of every level through the runner, in the problem's language |
| D9 (new) | The reference passes the generated test files of every level and the starter's own test files, through the native suite |
| D2, D4, D5 | Not applicable: no generator in the first phases |

Ready criteria: those of progressive problems (`authoring.md:227`, `domain/ready_criteria.py:143-165`), raised to at least 2 visible cases per level, since the visible cases are the only tests a user has before submitting; one reference approach with its explanation and `### Design`; a starter `README.md`. Everything is checked in the problem's one language: "every language in `languages`" is that language.

Conformance gains fixtures from 9022 on, each listing the languages that support projects: a two-file project per language for the grading path (a package import and a relative import), and a suite fixture per framework (a pass, a failure, an error, a hang, output, a crash).

Porting a project to another language is ordinary authoring of a new problem, built from scratch: the statement wording can be reused with the language's method names, and the starter, `tests.json`, reference and explanation are new. Cases being data would let a port start from its sibling's `tests.json`; this proposal follows the owner's rule and writes them for the new problem. Both problems list each other in `related`, and `catalog.md` gets a row for each.

## 7. Relationship to existing kinds

| Kind or problem | Recommendation |
|-----------------|----------------|
| `progressive` | Stays as is: one file, six languages, the same exercise in every language. It shares the level code with `project` |
| `0187-banking-system`, `0248-scheduled-transfers-bank` | Stay unchanged and progressive. Converting them would remove their six-language versions |
| New `0249-bank-project-python`, `0250-bank-project-typescript` | Project problems with 0248's behavior and its statement wording, in each language's names. Each has its own `tests.json`, covering the rules 0248's cases pin down with at least two visible cases per level, and its own starter, reference and explanation. `related` links the two and 0248, and 0248 may list them back |

## 8. What the future web UI needs

| Need | What this design provides | Phase |
|------|---------------------------|-------|
| File API boundary | `projects/<slug>/`: list, read, write, create, rename and delete inside it only (no `..`, no links out), ignoring caches and `.venv`. A starter manifest (path and digest of each seeded and generated file) for "changed", "added" and "restore" | 1 (folder), 3 (manifest) |
| Run and test API | `cstudy test --json`, `cstudy submit --json` and `cstudy status --json`, stable documents in the style of `cstudy test --json` (`cli.md:338-375`) | 1 |
| Streamed output | `--events`: one JSON line per event as it happens (build started and finished, diagnostics with file, line and column, test started and finished, level opened), forwarded from the runner's own event stream | 3 |
| Level state | `cstudy status --json`: unlocked level, titles of the open levels, best tally per level, timer, attempt id, statement path | 1 |
| Terminal | The native command works in the folder without `cstudy` (`.venv/bin/pytest`, `node --test`), so a terminal there needs only the workspace toolchains on `PATH` | 1 |
| Concurrent clients | A lock per project around generated-file writes and unlocks, so a UI and a terminal can run at once; compiled builds already lock (`runners.md:39,57`) | 3 |
| Product scope | The PRD lists a web UI as a non-goal and runs user code without a sandbox (`../prd.md:60,116`); the UI work starts by amending both | Later |

## 9. Risks and open questions

### Owner decisions

Ordered by how much they change the design. Each lists the options and a recommendation; none is decided here.

| Id | Decision | Options | Recommendation | Changes |
|----|----------|---------|----------------|---------|
| O1 | When hidden cases run, and what opens a level | (a) every `cstudy test` runs visible and hidden cases and opens levels, as progressive problems do; (b) `cstudy test` runs the native suite only, and `cstudy submit` grades and opens levels; (c) as (b), but a level opens once its visible tests pass, and submissions only score | (b): it practices the realistic loop of testing your own edge cases before submitting | Commands, data model, the web UI's two actions |
| O2 | Where visible tests come from | (a) generated from `tests.json` (option D); (b) hand-written native files in `starter/` (option C); (c) both | (a), with optional extra files from the author | Authoring cost, drift, cost of a port |
| O3 | Later-level methods in the starter | (a) every method stubbed from the start with its level, as progressive stubs are (`problem-format.md:423`); (b) only level 1's methods, and each level's statement names the methods to add | (b): designing for changes you cannot see yet is the point of a staged project | Starter, grading signature, statement |
| O4 | What a failing hidden case shows | (a) its input, as PRD Q10 decided (`../prd.md:150`); (b) a count only; (c) (a) in practice attempts and (b) in mock attempts | (c) | Report, `--json` |
| O5 | Grade and time box of a project attempt | Grade: (a) as today, a rating only after a full pass, otherwise `--gave-up`; (b) a rating once level 1 passes, capped by the levels passed (all: no cap; all but the last: `hard`; fewer: `again`). Time box: (i) soft, capping the grade as today; (ii) hard, refusing submissions after it | (b) and (i) | `done`, scheduling, `mock` |
| O6 | References per level | (a) one final reference; (b) a snapshot per level, shown by `cstudy solution --level N` | (a); (b) only if seeing the code evolve proves worth about four times the reference work | Content, verify cost |

### Technical unknowns

| Id | Unknown | Spike |
|----|---------|-------|
| K1 | Python editors and `uv` in a folder with a tool-only `pyproject.toml` and a `.venv` link: pyright, ruff and LazyVim find the interpreter; what `uv run pytest` does there | Phase 0, before the starter format is fixed |
| K2 | A suite restarted after a hung or crashed test (pytest `--deselect`, `node:test` name filters); pytest's capture and assertion-rewrite cache next to the runner's capture and source-only loading; breakpoints under `--inspect-wait` with `isolation: "none"` | Phase 1 for pytest, phase 2 for `node:test` |
| K3 | TypeScript editor types through `typeRoots` pointing at the shared install; `tsc -p` on a project from the workspace's TypeScript | Phase 2 |
| K4 | JVM: warm p50 of compiling main and test source sets plus a JUnit Platform launch, against NFR-1's 3 s for Java and 5 s for Kotlin; JUnit offline | Opens phase 4; may reopen ADR 0007 |
| K5 | Go: one module per project in `go.work` for gopls, and the overlay registration in a project package | Opens phase 5 |
| K6 | Rust: `cargo test` results on stable Rust, the cost of two profiles, and a harness that depends on a path crate | Opens phase 5 |

### Risks

| Risk | Mitigation |
|------|------------|
| Two kinds with levels drift apart | One level module for both; exhaustive `match` on `ProblemKind`, as on `Language` (`architecture.md:76`) |
| Loader changes break single-file problems | The new paths are keyed on the project target; `cstudy verify --conformance` and a full `cstudy verify` gate every runner change (`authoring.md:312`) |
| A user module shadows a standard-library module once the project root is on `sys.path` | S15 for the starter; the runner imports its own dependencies before it adds the root |
| Generated tests read like machine output | Show the pilot's generated files to the owner during phase 1 (O2); option C is the fallback |
| Grading depends on the entry class staying where the problem says | The README and `## Project` state the contract, and a missing entry is a `load_error` that names the expected module and class |
| Your own tests hang, print or crash | The suite runs under the case rules: hang guard, 4 KiB output limit, crash restart (`runners.md:136,179-190`) |
| The one-language rule is mistaken for a gap in the catalog | Coverage lines count a project only in its language; S13's message names the project exception |

## 10. Phased plan

Each phase is usable on its own.

| Phase | Delivers |
|-------|----------|
| 0 | An accepted design: owner decisions, ADR 0014, spec amendments |
| 1 | The Python pilot end to end: `bank-project-python`, playable from `start` to `done` |
| 2 | The TypeScript pilot: `bank-project-typescript`, and a second framework through the same suite protocol |
| 3 | Web UI groundwork in the CLI: an event stream, structured diagnostics, the starter manifest and `--restore`, a run lock |
| 4 | Java and Kotlin projects, after spike K4 |
| 5 | Go and Rust projects, after spikes K5 and K6 |

Sizes are a planning heuristic in authored changed lines: S under about 150, M about 150 to 400, L over 400.

| Id | Task | Route | Size |
|----|------|-------|------|
| PJ0.1 | Owner decisions O1 to O6, one at a time | Parent | - |
| PJ0.2 | Spike K1 in a scratch workspace | Delegated explorer | S |
| PJ0.3 | ADR 0014 and the spec amendments: problem-format, runners, cli, authoring, installation-and-workspaces, progress-and-scheduling, catalog, the PRD (FR-2, FR-3, the six-language rule), the docs index | Delegated writer | L |
| PJ1.1 | Domain and schema: `ProblemKind.PROJECT`, the `project` block, one level helper for both kinds, S13 exception, S14 to S16 | Delegated writer | M |
| PJ1.2 | Workspace: `projects/` in the template, copying the starter, the `.venv` link, archiving the folder, file targets under `projects/`, folder hash and watch | Delegated writer | M |
| PJ1.3 | pytest test generator; statement op names in the problem's language | Delegated writer | M |
| PJ1.4 | Python runner: project target, source loading under the root, bytecode prefix, signature cut by level, `suite` job hosting pytest, restart (K2), conformance fixtures | Delegated writer | L |
| PJ1.5 | CLI: `start`, `test`, `submit`, `status`, `done` rules, `--json`, `--debug`; migrations for `submissions` and `level_unlocks` | Delegated writer | L |
| PJ1.6 | Verify and doctor: D1, D3 and D9 for projects, ready criteria, the `project-python` template for `cstudy new`, the pytest WARN | Delegated writer | M |
| PJ1.7 | Content: `0249-bank-project-python` (starter; its own `tests.json` covering 0248's rules, at least two visible cases per level; reference; explanation), its catalog row, `related` on 0248 | Delegated writer | L |
| PJ1.8 | Exit check: `cstudy verify --require-ready` passes; a manual run through four levels; warm p50 of `cstudy test` and `cstudy submit` within 1.0 s | Delegated verifier, parent spot check | S |
| PJ2.1 | `node:test` test generator | Delegated writer | M |
| PJ2.2 | TypeScript runner: project launch, signature cut, `suite` job hosting `node:test`, restart and inspector (K2), `--typecheck` on a folder (K3), conformance fixtures | Delegated writer | L |
| PJ2.3 | Content: `0250-bank-project-typescript`, built from scratch as a new problem with 0249's statement wording; the `project-typescript` template | Delegated writer | L |
| PJ2.4 | Exit check as PJ1.8 | Delegated verifier, parent spot check | S |
| PJ3.1 | `--events` stream for `test` and `submit`; diagnostics with file, line and column | Delegated writer | M |
| PJ3.2 | Starter manifest, file states in `status`, `cstudy start --restore <path>` | Delegated writer | M |
| PJ3.3 | Lock per project around generated files and unlocks | Inline | S |
| PJ4.1 | Spike K4 | Delegated explorer | S |
| PJ4.2 | JVM project build, JUnit suite through the Launcher API, JUnit 5 and kotlin.test generators | Delegated writer | L |
| PJ4.3 | A first JVM project problem, in the language the owner picks | Delegated writer | L |
| PJ5.1 | Spikes K5 and K6 | Delegated explorer | S |
| PJ5.2 | Go project module, `go test -json` suite, generator | Delegated writer | L |
| PJ5.3 | Rust project crate, `cargo test` suite, harness on a path crate, generator | Delegated writer | L |

**Pilot slice.** The first runnable slice of phase 1 is PJ1.1 to PJ1.5 with a draft 0249 that has level 1 only: `cstudy start` seeds the folder and `tests/test_level_1.py`, `cstudy test` runs pytest through the runner, and `cstudy submit` grades level 1 and opens level 2. PJ1.6 and PJ1.7 then complete the checks and the remaining levels.

**What the TypeScript pilot proves that the Python one does not.**

- The `suite` job is framework-neutral: `node:test`'s event stream feeds the same protocol and report as pytest's hooks.
- A self-contained ESM folder resolves outside the shared `typescript/` project: its own `package.json`, explicit `.ts` imports, no `#support` and no `node_modules`.
- How the TypeScript runner builds a folder: nothing compiles, so the type check is the folder's build step (`tsc -p`), and the erasable-syntax rule must hold for the starter and the reference.
- The port: a second language version built from scratch as a separate problem from the same statement wording, which measures what the one-language decision costs per version.
- Tests debugged in-process under the Node inspector.

## Alternatives considered

| Alternative | Why not recommended |
|-------------|---------------------|
| A `layout: project` flag on `progressive` instead of a new kind | Projects differ in layout, start, grading, references, verify, bench and languages; a flag would hide those branches from the exhaustive `match` on `ProblemKind` |
| Project folders inside the language projects (`python/projects/<slug>/`) | Inherits the venv and `node_modules` with no configuration, but is not one folder on the JVM (main and test sources sit apart in the shared Gradle tree) and Go and Rust need their own module or crate anyway |
| A venv or `node_modules` per project | The most standalone, but every start needs the network (NFR-6) and disk use multiplies |
| Run the native tool and parse its report (JUnit XML, `--test-reporter=junit`) instead of hosting the framework in the runner | Less code per language, but loses the per-test hang guard, the crash restart, per-test output capture and the debug launch the runner already has |
| Vitest or Jest for TypeScript | Familiar, but they need a network install and their own transform; `node:test` ships with Node 24 and runs `.ts` through type stripping |
| unittest for Python | Nothing to install, but pytest is what Python projects use, and its failure messages are clearer; the cost is one dev dependency in the shared venv |
| Convert 0187 and 0248 into project problems | Loses their six-language single-file versions |
