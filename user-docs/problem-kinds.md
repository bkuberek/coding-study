---
title: Kinds of problems
summary: The tracks, the kinds of problem and how each is checked, why any approach that passes counts, how a signature reads in each language, the labels, and what concurrency and debugging problems ask of you.
section: Practise
order: 55
---

# Kinds of problems

Every problem has a **track**, the interview round it practises, and a **kind**, the shape of what you write. How it is checked follows from its kind, and three **labels** say what it is about, who it is for and how big it is. `cstudy list` shows each, and filters by each:

```bash
cstudy list --track concurrency
cstudy list --kind project
cstudy list --checked-by rubric
cstudy list --domain security --scope function
```

## Tracks

| Track | What you practise | Checked by |
|-------|-------------------|------------|
| `dsa` | Data structures and algorithms | tests |
| `practical` | Work-like problems: classes that grow over levels, and projects of several files, services among them | tests |
| `lld` | Object-oriented and low-level design: an API the tests check, and a design you compare with a rubric | tests and rubric |
| `concurrency` | Code that several threads or tasks call at once | tests |
| `debugging` | Finding and fixing a bug in code that looks right | tests |
| `system-design` | Designing a system, in notes | rubric |
| `code-review` | Reviewing a change, in notes | rubric |
| `behavioral` | Behavioural rounds. The track has no problems: prepare from a story bank of your own | - |

`cstudy list` shows the tracks in this order, and `cstudy next --track system-design` picks within one track.

## Kinds

| Kind | You write | Tracks |
|------|-----------|--------|
| `function` | One function, called with each case's input | `dsa`, `practical`, `debugging` |
| `design` | A class, tested by a sequence of calls and the results each returns | `dsa`, `practical`, `lld`, `debugging` |
| `progressive` | One class that grows over levels: a run that passes the open levels opens the next ([progressive problems](levels.md#progressive-problems)) | `practical` |
| `concurrent` | A class whose methods several workers call at the same time ([below](#concurrency-problems)) | `concurrency` |
| `project` | A folder of files in one language, with tests you run in your language's own tool, graded level by level with `cstudy submit` ([project problems](levels.md#project-problems)). A service project is one too, graded over HTTP ([service projects](service-projects.md)) | `practical` |
| `system-design` | Notes: requirements, estimates, API, data model, high-level design, deep dives and trade-offs | `system-design` |
| `code-review` | Notes: the issues of a change, by severity, each with its location and the change you would ask for | `code-review` |

The first five run your code in a language you choose from those the problem lists. The last two have no language: `cstudy start` writes a notes file for your answer ([system design and code review](practice.md#system-design-and-code-review)).

## Checked by

| Checked by | How | Problems |
|------------|-----|----------|
| `tests` | `cstudy test`, or `cstudy submit` for a project, runs your code against the cases and gives the verdict | Every kind that runs code |
| `rubric` | You compare your answer with a rubric and a reference answer, and your rating is the grade | `system-design` and `code-review` problems, and `lld` problems, whose tests check the API |
| AI review | Planned: an optional review of a rubric answer. It is not available yet | None yet |

`cstudy list --checked-by tests` and `--checked-by rubric` filter by it, and the web UI's Problems view has a Checked by column, `tests`, `tests + rubric` or `rubric`, with a filter. In the `--json` output of `cstudy list`, `cstudy next` and `cstudy status`, `checked_by` lists the values.

## Any approach that passes

Correctness is behavioral. `cstudy` sends each case's input to your code, takes what your code returns, and compares that with the expected value. Your code never sees the expected values, and nothing reads, parses or diffs your code, or compares it with a reference solution. So any approach that passes the tests passes: a loop or recursion, a library call or your own data structure. A result whose order does not matter is compared without its order, and where a problem has several right answers, a checker validates yours instead of comparing it with one value.

| Not part of passing | Where it counts |
|---------------------|-----------------|
| Speed | Time limits are off unless you turn them on, with `cstudy test --time-limit` or in your [configuration](commands.md#configuration-keys) |
| How your time grows | `cstudy bench` gives a verdict; with the default settings, a `suboptimal` verdict at medium or high confidence caps the grade at `hard` ([measure your solution](practice.md#measure-your-solution)) |
| Style | Never checked: what has to match is the function or class that the starter declares, which the cases call |

## One signature in every language

A problem states its function or class once, and `cstudy start` writes your starter from it in the language you chose, with the names in that language's style:

| Canonical | Python | TypeScript | Java | Kotlin | Go | Rust |
|-----------|--------|------------|------|--------|----|------|
| Function `twoSum` | `two_sum` | `twoSum` | `Solution.twoSum` | `Solution.twoSum` | `twoSum` | `two_sum` |
| Class `LRUCache` | `LRUCache` | `LRUCache` | `LRUCache` | `LRUCache` | `LRUCache` | `LRUCache` |
| Its constructor | `LRUCache(...)` | `new LRUCache(...)` | `new LRUCache(...)` | `LRUCache(...)` | `NewLRUCache(...)` | `LRUCache::new(...)` |
| Method `getRandom` | `get_random` | `getRandom` | `getRandom` | `getRandom` | `GetRandom` | `get_random` |

Python takes a function at module level, and Java and Kotlin a method of `class Solution`. The types map the same way in every problem:

| Type | Python | TypeScript | Java | Kotlin | Go | Rust |
|------|--------|------------|------|--------|----|------|
| `int` | `int` | `number` | `int` | `Int` | `int` | `i32` |
| `long` | `int` | `number` | `long` | `Long` | `int64` | `i64` |
| `double` | `float` | `number` | `double` | `Double` | `float64` | `f64` |
| `string` | `str` | `string` | `String` | `String` | `string` | `String` |
| `int[]` | `list[int]` | `number[]` | `int[]` | `IntArray` | `[]int` | `Vec<i32>` |
| `list<string>` | `list[str]` | `string[]` | `List<String>` | `List<String>` | `[]string` | `Vec<String>` |
| `decimal` | `Decimal` | `Decimal` | `BigDecimal` | `BigDecimal` | `decimal.Decimal` | `Decimal` |
| `date` | `date` | `IsoDate` | `LocalDate` | `LocalDate` | `time.Time` | `NaiveDate` |
| `TreeNode` | `TreeNode \| None` | `TreeNode \| null` | `TreeNode` | `TreeNode?` | `*TreeNode` | `Option<Rc<RefCell<TreeNode>>>` |
| No result | `None` | `void` | `void` | `Unit` | none | `()` |

| Rule | Detail |
|------|--------|
| The same cases | Every language runs the same cases, so a `long` stays within what a TypeScript `number` holds exactly, and no expected value depends on integer overflow |
| Money and days | `decimal` is exact base-10 arithmetic and `date` a calendar day; both travel as text, never as floating-point numbers |
| Exact types in Go and Rust | Keep the types of the starter. Another type, such as `[]int64` for `int[]` in Go or `&[i32]` in Rust, does not load: the run ends with exit 2 |

## Labels

Three labels describe every catalog problem, apart from its track, kind and difficulty: a project can be easy and a function hard, and a security problem is a `practical` or `debugging` one with the domain `security`.

| Label | Filter | How many | Answers |
|-------|--------|----------|---------|
| Domain | `--domain <domain>` | One or more | What is it about? |
| Role | `--role <role>` | One or more | Who is it for? |
| Scope | `--scope <scope>` | Exactly one | How big is the thing you work on? |

| Domain | Means |
|--------|-------|
| `algorithms` | Data structures and algorithms, language pitfalls |
| `backend` | Services, APIs, data, the design of backend components |
| `security` | Authorisation, tenancy, validation, defensive engineering |
| `identity` | Tokens, sessions, login flows, provisioning |
| `ai-llm` | The code around models: clients, retrieval, evaluation, cost |
| `fintech` | Money, ledgers, insurance |
| `data` | Data engineering: pipelines, streams, tables, quality, lineage |
| `infrastructure` | Infrastructure as code, configuration, deployment tooling |
| `systems` | Operating systems, networking, the mechanics of distributed systems |
| `software-design` | Testing, refactoring, design patterns, architecture |
| `frontend` | Browser UI, state, rendering, accessibility |

| Role | For |
|------|-----|
| `general` | Any software engineer |
| `backend` | Backend engineers |
| `platform` | Platform and infrastructure engineers |
| `security-engineer` | Security engineers |
| `ai-engineer` | Engineers who build on models |
| `ml-engineer` | Engineers who train and evaluate models |
| `data-engineer` | Engineers who build and run data pipelines and tables |
| `frontend` | Engineers who build browser UIs |

| Scope | Means |
|-------|-------|
| `function` | One function or class, in one file |
| `project` | A folder of files |
| `system` | Several services, such as the designs of the `system-design` problems |

`cstudy list` and `cstudy next` take each filter once. A filter keeps the problems that list its value, so `--role security-engineer` keeps only the problems written for security engineers, not every problem with `general`.

## Concurrency problems

A concurrency problem is a class whose methods several workers call at once. It has two kinds of case:

| Case | Runs | Passes when |
|------|------|-------------|
| Sequential | Once, one call after another, as a design problem's | Every result is the expected one |
| Stress | Many times, with workers that call your methods at the same time, then an optional final sequence | Every run ends without an error or a stall, and every invariant of the case holds |

A stress case passes only when every run passes: one failing run is a real bug, since correct code holds its invariants on every schedule. Otherwise it shows the first failing run's status, `FAIL`, `ERROR`, `INVALID`, `STALLED` or `TIMEOUT`, how many runs passed, and the seed of each failing run. A pass is evidence, not proof: a race can stay hidden in the runs you made.

| Language | Workers are | Each problem runs |
|----------|-------------|-------------------|
| Java, Kotlin | Threads | On platform threads and on virtual threads, as the problem lists, each with its own verdict |
| Python | Threads or `asyncio` tasks, as the problem says | Once |
| TypeScript | Async tasks on one event loop | Once |
| Go | Goroutines | Once |
| Rust | Threads | Once |

A problem lists only the languages where its race can show, so not every one has all six.

```bash
cstudy test --stress 20                          # more runs of each stress case
cstudy test --case s1 --seed 1007 --stress 1     # one run, with a failing run's seed
cstudy solution bounded-blocking-queue --broken  # a broken reference: spot the bug
```

With tasks on one event loop, a seed repeats the same schedule, so a failing run's seed reproduces it exactly. With threads it does not: more runs raise the chance of seeing it again. `cstudy solution <slug> --broken` shows a deliberately broken reference with the explanation of its bug; the stress cases are written to catch each one.

## Debugging problems

A problem of the `debugging` track starts from code that looks right and has a bug. `cstudy start` writes that code as your file, instead of an empty stub. At least one case fails in every language, while the visible examples may pass, so you first find the input that breaks it, then fix the code until `cstudy test` passes.

Some bugs belong to one language, such as integer overflow, mutable default arguments or boxed equality, so the problem lists only the languages that have them; Go and Rust have bugs of their own. `cstudy solution` shows the fixed code, and the explanation names the bug and the general trap behind it.

Every language has debugging problems:

| Languages | Problems such as |
|-----------|------------------|
| Python, TypeScript, Java and Kotlin | `debug-binary-search-bounds`, `debug-recursion-base-case`, `debug-sort-comparator` |
| TypeScript | `debug-falsy-plan-update`, `debug-stale-closure-callbacks`, `debug-invoice-total-cents` |
| Python | `debug-mutable-default-argument` |
| Java and Kotlin | `debug-boxed-equality`, `debug-running-total-overflow` |
| Go | `debug-append-aliasing`, `debug-nil-map-write`, `debug-shadowed-variable` |
| Rust | `debug-char-boundary`, `debug-float-ordering`, `debug-unsigned-underflow` |

`cstudy list --track debugging --lang go` lists those you can work on in one language. A project of the `practical` track can start from buggy code too, such as `debug-async-batch-typescript`.

To step through any problem's code with your IDE's debugger, see [debug a run](ide-and-debugging.md#debug-a-run).
