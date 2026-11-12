# Spec: Authoring Problems

User-authored problems are first-class: the shipped catalog and your own problems use the same format, the same `cstudy new` scaffolding and the same `cstudy verify` gate. This page defines the workflow, the mandatory description and explanation formats, and every check `cstudy verify` runs.

## Workflow

| Step | Action | Check |
|------|--------|-------|
| 1 | `cstudy new <slug> --from-template array --pattern <id> --difficulty medium` | directory created with `status: draft` |
| 2 | Write `problem.md`: statement, input, output, constraints, in original wording | `cstudy verify <slug> --static` |
| 3 | Set `signature` and `comparator` in `meta.yaml`, and edit the [labels](content.md#labels) `cstudy new` wrote from its template (`domains`, `job_roles`, `scope`) to fit the problem | `--static` type-checks tests against the signature, and S24 the labels |
| 4 | Add visible examples to `tests.json` and their explanations in `problem.md`; add hidden edge cases | `--static` |
| 5 | Write the brute-force approach in Python with `oracle: true` | `cstudy verify <slug>` |
| 6 | Write `generator.py` (and `validate`) | `cstudy verify <slug> --oracle` |
| 7 | Write the optimal approach(es): Python first, then TypeScript, Java, Kotlin (and Go and Rust when `languages` lists them, [ADR 0012](../decisions/0012-go-and-rust.md)) | `cstudy verify <slug> --oracle` |
| 8 | Write `solutions/explanation.md`, one section per approach | `--static` |
| 9 | Add the `perf` block and `generate` cases at the largest ladder size | `cstudy verify <slug> --ladder` (Phase 2 on) |
| 10 | Set `status: ready` | `cstudy verify <slug> --oracle --ladder --require-ready` |

Where step 1 writes depends on the content root ([installation-and-workspaces](installation-and-workspaces.md#your-own-problems)): in a content checkout (`uv run cstudy` there, `--content` or `CSTUDY_CONTENT`) into the checkout's `problems/`; with the content bundled in an installed `cstudy`, into your workspace's own `problems/`, numbered from 5001 and overlaid on the catalog. Every later step works the same in both places.

Concurrent problems (`cstudy new <slug> --from-template concurrent`) replace steps 5, 6 and 9:

| Step | Action | Check |
|------|--------|-------|
| 5c | Write the sequential cases (they never block) and the optimal approach in one threads language | `cstudy verify <slug>` |
| 6c | Write stress cases and their invariants ([problem-format](problem-format.md#stress-cases)) | `cstudy verify <slug> --static` |
| 9c | Write the broken references in `solutions/broken/` and tune the scenarios until each is caught | `cstudy verify <slug> --require-ready` (D6, D7) |

Project problems follow [their own workflow](#project-problems).

A problem whose Java and Kotlin code needs a feature that JDK 21 lacks declares `jdk: {min: N}` in `meta.yaml` before step 7, so that `cstudy verify` builds its references at release `N` and rejects an API newer than the declared minimum ([JDK range](problem-format.md#jdk-range)). A problem declares nothing otherwise: a missing bound is the bound of the supported range.

A problem may stay `draft` with references in only some languages. Drafts are fully practicable (tests are language-neutral) but `cstudy next` skips them, and time limits by factor need an optimal reference in the attempt's language.

## problem.md

Every problem has a full description. Required headings, in order:

| Heading | Content | Enforced |
|---------|---------|----------|
| `# <title>` | Equals `meta.title` | yes |
| `## Statement` | The task in original wording | non-empty |
| `## Input` | Each parameter (design problems: constructor and methods) with meaning | non-empty |
| `## Output` | Return value and any "any order" or "any valid answer" rule | non-empty |
| `## Examples` | At least one `### Example <n>`, each with exactly one `<!-- case: <id> -->` marker and at least one line of explanation | marker ids exist, are `visible`, and every visible case is referenced exactly once |
| `## Constraints` | Bullet list of size and value ranges | non-empty |
| `## Follow-ups` | Optional extensions, often hinting at the optimal approach | optional |
| `## Hints` | Optional `### Hint <n>`, numbered from 1, most general first | numbering |

Progressive problems replace `## Examples` with one `## Level <n>: <title>` section per level, titled as in `meta.yaml` and in level order. Each level section starts with that level's operations and rules, then holds its own `### Example <n>` subsections (only examples: every `###` subsection needs a marker), and the example of a level-`L` visible case sits in `## Level L`. `## Statement`, `## Input`, `## Output` and `## Constraints` are shown at every level, so they describe only what holds for all levels and never a later level's rules ([progressive problems](problem-format.md#progressive-problems)). Project problems also require a non-empty `## Project` section after `## Output`, written in the problem language's names ([statement](problem-format.md#statement)). Concurrent problems add a required `## Concurrency` section after `## Constraints`: which methods are called concurrently, which block and until when, the ordering guarantee (for example FIFO), and the model per language. The rendered statement appends to it a generated table of the stress cases (id, note, worker groups with count and iterations, invariant types), so the user knows what is checked. No section may contain the placeholder text `TODO`, in prose or in code: the check matches the four letters anywhere, so a `## Project` section describes a starter stub by what it does, not by its source. Kotlin's `TODO()` stub is one that throws `NotImplementedError`, and Rust's `todo!()` stub is one that panics.

The example marker is replaced in the rendered statement by the case's input and expected output, so example data has one source (`tests.json`) and cannot drift. Values print as JSON, except that `decimal` and `date` values print without quotes, as the signature types them (`premium = 2500.50`, `[2026-01-01, 2026-07-01]`), so a statement never needs to explain the quotes. Hints never appear in the rendered statement; `cstudy hint` reveals them one at a time.

```markdown
# Two Sum

## Statement

You get an integer array `nums` and an integer `target`. Exactly two positions hold values that add up to `target`. Return those two positions in any order.

## Input

- `nums`: the integers to search
- `target`: the required sum

## Output

Two distinct indices `i` and `j` with `nums[i] + nums[j] == target`, in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The values at positions 1 and 2 are 9 and 2, and 9 + 2 = 11.

### Example 2

<!-- case: ex2 -->

Equal values at different positions form a valid pair.

## Constraints

- `2 <= nums.length <= 10^5`
- `-10^9 <= nums[i], target <= 10^9`
- Exactly one valid pair exists.

## Follow-ups

- Can you beat O(n^2) time?

## Hints

### Hint 1

For each value, which partner would complete the sum?

### Hint 2

Remember the values already seen, together with their positions.
```

## explanation.md

One file per problem, `solutions/explanation.md`, so approaches can be compared side by side. Every approach in `meta.yaml` has a section; every section belongs to an approach.

```markdown
# Two Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny or memory is extremely tight |
| hash-map | optimal | O(n) | O(n) | default answer |

## Approach: hash-map (One-pass hash map)

### Intuition

### Algorithm

### Correctness

### Complexity

- Time: O(n) — each element is visited once; map lookups and inserts are O(1) on average.
- Space: O(n) — the map holds up to n - 1 entries.

### Trade-offs

### Pitfalls and edge cases

### Language notes
```

| Subsection | Content | Enforced |
|------------|---------|----------|
| `### Intuition` | The key insight in a few sentences | required, non-empty |
| `### Algorithm` | Numbered steps | required, non-empty |
| `### Correctness` | Why it always returns a right answer (invariant, exchange argument, induction) | required, non-empty |
| `### Complexity` | Lines starting `- Time: <meta time>` and `- Space: <meta space>`, each with a justification | required; strings must equal `meta.yaml` |
| `### Trade-offs` | Versus the other approaches: speed, memory, simplicity, interview suitability | required, non-empty |
| `### Pitfalls and edge cases` | Off-by-one traps, empty input, duplicates, overflow, mutation | required, non-empty |
| `### Language notes` | Where idioms differ: Kotlin `IntArray` versus `List<Int>`, Java boxing and `Integer` equality, Python `heapq` being a min-heap, TypeScript lacking a built-in heap | required for `optimal` approaches when the four reference files use different data structures or library calls; otherwise optional (missing: warning) |

Sections appear in `meta.yaml` approach order, ladder from brute to optimal. `## Overview` rows must match the approaches' ids, roles, time and space.

A project problem's one approach section adds a required, non-empty `### Design` subsection after `### Algorithm`: the files of the reference and what each is responsible for. `### Language notes` is optional for it, and missing it is no warning.

Concurrent problems follow the approach sections with one section per broken reference, in `concurrency.broken` order. They are not in `## Overview`. For concurrent problems `### Language notes` is required for every `optimal` approach and covers Java platform versus virtual threads, Python's GIL (or asyncio), TypeScript's event loop when listed, Go's `sync` primitives and channels and Rust's `Mutex`, `Condvar` and `&self` sharing when listed (or why an approach has no Go or Rust reference), and, when Kotlin is listed, how the same design would look with coroutines (`Mutex`, `Semaphore`, `Channel`), since coroutines are not autograded in v1 (PRD Q5).

```markdown
## Broken: if-not-while (Wait guarded by if)

### Bug

### Failing interleaving

### Fix
```

| Subsection | Content | Enforced |
|------------|---------|----------|
| `### Bug` | What is wrong and which invariant or status exposes it | required, non-empty |
| `### Failing interleaving` | One concrete schedule, step by step, that breaks it | required, non-empty |
| `### Fix` | The smallest change that makes it correct, pointing to the approach that does it | required, non-empty |

## rubric.md

Low-level design problems (track `lld`) have `rubric.md` next to `problem.md`. The ops tests check the public behavior; the rubric covers the design, for self-review after `cstudy done`. `cstudy solution` shows it before the explanation and the code. Required `##` sections, in order:

| Section | Content | Enforced |
|---------|---------|----------|
| `## Responsibilities` | Which class owns which decision and which data | at least one `- [ ] <criterion>` item |
| `## Extension points` | Changes the design absorbs without editing callers | at least one `- [ ] <criterion>` item |
| `## Patterns` | Patterns or seams a strong answer uses, and why | at least one `- [ ] <criterion>` item |
| `## Testability` | How behavior is observed and isolated (no clock, randomness or I/O) | at least one `- [ ] <criterion>` item |
| `## Reference design` | The reference classes, their relationships and the key trade-offs, in prose (a text diagram is welcome) | non-empty |

The title is `# <title>: Rubric`. Other `##` sections (for example `## Follow-ups`) are allowed; no required section may contain `TODO`. The checklist items are written as checks a reviewer can tick against their own code, not as instructions. Rubrics of the non-autograded tracks (`tracks/`) follow [content](content.md#non-autograded-item-format) instead: any `##` areas, each a checklist. `coding_study.domain.rubric` checks both formats with one criterion parser, which ignores checkboxes inside code fences.

```markdown
# Parking Lot: Rubric

## Responsibilities

- [ ] `ParkingLot` alone decides which spot a car gets; callers never compute spot numbers.

## Extension points

- [ ] Spot sizes can be added without changing callers of `park`.

## Patterns

- [ ] Choosing a spot is a natural strategy seam, even while only one policy exists.

## Testability

- [ ] All behavior is observable through the public API: no clock, randomness or I/O.

## Reference design

`ParkingLot` keeps an occupancy array indexed by spot number and a map from plate to spot ...
```

## Practical and low-level design problems

What a content stream writes for the `practical` and `lld` tracks, beyond what every problem needs (a `practical` project problem follows [Project problems](#project-problems) instead):

| Item | `practical` | `lld` |
|------|-------------|-------|
| `meta.yaml` | `track: practical`, `kind: progressive`, `levels` (at least 2, usually 4) with `level` and `title`, `level` on every method, `comparator: {type: ops}` | `track: lld`, `kind: design`, `comparator: {type: ops}` |
| API | One class; later levels add methods and may refine earlier rules; time is an explicit `timestamp` (`long`) argument, never a clock | One class or a facade class over the design; absence as sentinel values, never exceptions |
| `problem.md` | `## Statement`, `## Input`, `## Output`, one `## Level <n>: <title>` per level (operations, rules, examples), `## Constraints` | The usual sections with `## Examples` |
| `tests.json` | `level` on every case; per level at least 1 visible and 2 hidden cases | At least 2 visible and 8 hidden cases |
| Extra file | none | `rubric.md` ([format](#rubricmd)) |
| References | Every approach, implementing every level, in every language the problem lists (all six by default) | Every approach in every language the problem lists |
| Optional | `generator.py` (then `generate` cases at the last level, one at the largest ladder size), `patterns`, more approaches | Same |

A `function` or `design` problem on the `practical` track, such as the business tasks from `0214` and the security and AI/LLM problems from `0255`, has no levels and uses the usual sections with `## Examples`, and the ready criteria for its kind. `solutions/broken/` is for concurrent problems and projects with stress cases, and every approach must pass every case, so a wrong answer cannot be stored with such a problem: name it under `### Pitfalls and edge cases`, with the hidden case that catches it. A project without stress cases does the same: S12 refuses its `solutions/broken/`, and D7 requires a broken overlay to pass every sequential case, which is what a logic bug does not do.

### Project problems

A [project problem](problem-format.md#project-problems) (`kind: project`, track `practical`) is a seeded folder in one language ([ADR 0014](../decisions/0014-project-problems.md)). A version in another language is a new problem, authored from scratch: only the statement wording may be reused, with that language's names, and both problems list each other in `related`.

| Step | Action | Check |
|------|--------|-------|
| 1 | `cstudy new <slug> --from-template project-python` (or `project-typescript`, `project-go`, `project-java`, `project-kotlin`, `project-rust`): a starter with an entry class and two levels. `--virtual-clock` writes the variant for code that waits: `project.clock: virtual`, a level-2 method that waits (asynchronous where the language has the form), an example with `@spawn`, `@advance`, `@join` and `@now`, the starter's clock pieces and a README section on testing on the clock. `--stress` writes the variant for code that several threads or tasks share: a `concurrency` block, one stress case `s1` at level 2 and one broken overlay, `solutions/broken/lost-update/`, which the case catches. Java has `--stress` but no clock: `--virtual-clock` with `project-java` exits 3 with `--virtual-clock is not available for project-java: Java has no virtual clock`. Each flag exits 3 for a language its step has not reached, and `--stress` for TypeScript without `--virtual-clock`, since TypeScript's stress cases run in the `async` model, where a synchronous method is atomic and an asynchronous one needs the clock ([ADR 0017](../decisions/0017-async-project-problems.md#scope-and-order), [cli](cli.md#cstudy-new)) | `cstudy verify <slug> --static` |
| 2 | Write `problem.md` (with `## Project` and one `## Level` section per level) and `tests.json` (at least 2 visible and 2 hidden cases per level) | `--static` |
| 3 | Shape the starter: the entry class with level 1's methods, the seeded files, the build files, `README.md` | `cstudy verify <slug>` (D1) |
| 4 | Write the reference overlay in `solutions/<approach>/`, level by level | `cstudy verify <slug>` (D3, D9) |
| 4v | With the virtual clock: check that every case gives the same outputs in every run, and fix the expected values that depend on a tie ([checklist](#virtual-clock-checklist)) | `cstudy verify <slug>` (D10) |
| 4s | With stress cases: write the broken overlays in `solutions/broken/<id>/` and tune the cases until each is caught | `cstudy verify <slug> --require-ready` (D6, D7) |
| 5 | Write `solutions/explanation.md` with `### Design`; set `status: ready` | `cstudy verify <slug> --require-ready` |

The starter is what the user sees first, so it states the contract and nothing more: level 1's methods with "not implemented" bodies, no hint of later levels, and seeded files that a real codebase would have (model types, a test fixture) rather than a solution's structure. A project that trains working in code you did not write (`0262`, `0263`) starts from a service that already runs instead, and level 1 asks for a change to it, so the untouched starter still fails level 1. Its later levels may add no method, so they have no `Methods to add:` line. Fields a later level adds to a response break the earlier levels' exact cases, so the starter's response already has that shape, or the level adds a route or a method that reads the new result (`0276`). A rule a later level adds must leave the earlier cases' results alone: a new method turns it on (`0274`'s `setDeadline` and `setBreaker`), or its default gives the earlier behavior (`0274`'s jitter source, which answers 1 when nothing is scripted). A case runs in one process, so a project that needs a crash scripts one: an exception that stands for `kill -9`, and a method that replaces everything except the durable store (`0272`'s `crashAt` and `restart`).

A project whose code waits declares `project.clock: virtual` and writes its waiting cases with the [harness operations](problem-format.md#asynchronous-code-and-the-virtual-clock); a project whose code is shared between threads or tasks has [stress cases](problem-format.md#stress-cases-in-projects). Time-dependent behavior takes timestamps as arguments only in a project without the virtual clock.

A service project (`project.grading: http`) has its [own manifest](service-projects.md#manifest-sketch), [file layout](service-projects.md#where-the-files-live), [mock configs](service-projects.md#config-format), [HTTP cases](service-projects.md#hidden-http-case), and [checks and ready rules](service-projects.md#checks): `cstudy new <slug> --from-template project-typescript-service` (or `project-python-service`, `project-java-service`, `project-kotlin-service` or `project-go-service`) starts one, and `cli/tests/fixtures/service_projects/` holds small working ones in TypeScript, Python, Java and Go. A project whose starter passes level 1 untouched weakens `cstudy done`, so level 1 asks for one small change as well.

## Ready criteria

`status: ready` requires all of the following; `cstudy verify --require-ready` enforces them.

- Every static and dynamic check below passes.
- At least one `optimal` approach has a reference file in every language in `languages`, which defaults to all six in the catalog and to the four core languages in a workspace problem without the line ([ADR 0012](../decisions/0012-go-and-rust.md)).
- Every approach has a reference file in each of its languages: every language in `languages`, unless a `concurrency` or `debugging` approach names fewer in its own `languages` ([Approaches](problem-format.md#approaches-and-complexity)).
- `dsa` problems: at least 2 approaches (a slower one, or an alternative optimal technique when no slower approach is meaningful), an `oracle` approach in Python, and `generator.py`.
- `tests.json`: at least 2 visible cases, at least 8 hand-written hidden cases, and, for `dsa` problems and any problem with `generator.py`, at least 1 `generate` case at the largest ladder size.
- `progressive` problems: at least 2 levels; every level has at least 1 visible case and at least 2 hand-written hidden cases.
- Service projects: the [ready rules](service-projects.md#ready-rules) on top of these; D11 passes, and without a usable Docker engine `--require-ready` counts the problem as not passed.
- `project` problems: the `progressive` rules above, raised to at least 2 visible and 2 hand-written hidden cases per level, since the visible cases are the only tests a user has before submitting; exactly one approach, `optimal`, with its overlay and its `### Design` subsection; a starter with `README.md`; D9 passes. "Every language in `languages`" is the problem's one language, and the `dsa` rules on generators, oracles and `generate` cases do not apply. A virtual-clock problem also passes D10. A project with stress cases has at least 2 of them, at least one broken overlay, and every broken overlay caught (D7), and the slowest correct run of every stress case uses at most 25% of its `deadline_ms`, as for `concurrent` problems.
- `lld` problems: `rubric.md` present with every required section ([rubric.md](#rubricmd)).
- `concurrent` problems: at least 2 visible and 4 hidden sequential cases; at least 2 stress cases; at least one broken reference for every language in `languages`; every broken reference caught (D7); the slowest correct run of every stress case uses at most 25% of its `deadline_ms` (margin against flaky stalls). The `dsa` rules on generators, oracles and `generate` cases do not apply.

## What `cstudy verify` checks

### Static (`--static` runs only these)

| Id | Check |
|----|-------|
| S1 | `meta.yaml` valid against `schemas/meta.schema.json`; `tests.json` against `schemas/tests.schema.json`; `item.yaml` against `schemas/item.schema.json` ([items](#items)) |
| S2 | Directory name equals `<id>-<slug>`; ids and slugs unique across `problems/` and `tracks/` |
| S3 | Signature parses with the type DSL; names valid; no reserved words after per-language conversion, in the languages the problem lists (a Rust keyword other than `self`, `Self`, `super` and `crate` is allowed: Rust writes it as a raw identifier, `r#move`); no Go function named after a package its stub imports (`time` where the signature uses `date`, `decimal` where it uses `decimal`) and no Rust class named after an imported type (`NaiveDate`, `Decimal`), since neither stub compiles. Warnings, not errors: a Python name that shadows a builtin (`sum`), the type the Python stub imports for the signature (`date` where it uses `date`, `Decimal` where it uses `decimal`), or a Go parameter named after an imported package ([naming rules](problem-format.md#naming-rules)) |
| S4 | Every case input and expected value conforms to the signature (ranges, char length, node encodings, op names and arities, the arguments and expected values of the harness operations of a [virtual-clock project](problem-format.md#asynchronous-code-and-the-virtual-clock) (`@spawn` takes a method's arguments, `@join` returns its result type), `long` at most 2^53-1, `decimal` and `date` strings; an expected `decimal` is canonical, [Decimal and date](problem-format.md#decimal-and-date)) |
| S5 | `problem.md` required headings, example markers and hint numbering; progressive and project: no `## Examples`, one `## Level <n>: <title>` per level as in `meta.yaml`, in order, each with at least one example, and each example in its case's level section |
| S6 | `explanation.md` sections and subsections per approach; complexity lines equal `meta.yaml`; overview table consistent |
| S7 | Every file in `solutions/` maps to a declared approach (for a project problem, every directory in `solutions/` is the declared approach or, in a project with stress cases, `broken/` (S12), and no reference file per language exists), and to one of its `languages` when the approach names them; every approach has at least one file; only `concurrency` and `debugging` approaches name `languages`, and only languages of the problem; at most one `oracle`, and it has a Python file |
| S8 | `checker.py` present if and only if `comparator.type` is `checker`; no `float` comparator (or `per_method` `float`) where the compared outputs hold `decimal` and no `double`, because decimals always compare exactly ([comparators](problem-format.md#comparators)); with `stub: buggy`, exactly one `buggy/solution.<ext>` per language in `languages`, and no `buggy/` otherwise; `rubric.md` for `lld`, and any `rubric.md` has the [required sections](#rubricmd) |
| S9 | `perf.expected_from` names a Python approach; `size_ladder` ascending |
| S10 | Progressive and project: levels contiguous from 1; every level has cases; every case `level` valid and using only methods introduced at or below it; `generate` cases at the last level |
| S11 | Concurrent: `kind: concurrent` if and only if `track: concurrency`; `concurrency.model` valid for every listed language; comparator `ops`; no `perf`, `oracle`, `time_class` or `generator.py`; `blocking` only on methods; `## Concurrency` section present |
| S12 | Concurrent stress cases: steps name signature methods (not the constructor) or harness ops with valid arity; template ranges fit the parameter types; `@enter`/`@exit` balanced and nested per iteration; selectors name existing ops and argument indexes; 2 to 64 workers and at most 20,000 ops per run after expansion; `stress_checker.py` present if and only if a `checker` invariant exists; every broken file maps to a declared broken id and every `caught_by` id is a stress case; `## Broken` sections match `concurrency.broken` |
| S13 | Every language in `languages` can express the problem, and a catalog problem outside the `concurrency` and `debugging` tracks lists every language that can (`must list rust: ...`), unless one of its domains is in `LANGUAGE_SUBSET_DOMAINS` (`security`, `identity`, `ai-llm`): any one of them lets it list any subset of the languages that can express it ([ADR 0020](../decisions/0020-catalog-labels.md#rule-changes)); the schema only requires one language. A problem in your own workspace (`cstudy new` without a content checkout) may list any subset, but a `dsa` problem keeps `python` for its oracle (S7). Rust cannot when a `ref_of` points into a `ListNode` (or `ListNode[]`), when an `as: index` result is a `ListNode` or indexes one, or when a case input holds a cyclic list (`cycle_at`): an `Option<Box<ListNode>>` has one owner per node ([mapping](problem-format.md#go-and-rust-mapping)). `no_alias_with` on a list is fine. A `project` problem is the fourth exception to `must list`, next to the subset tracks, the subset domains and workspace problems: it lists exactly one language (S14), and the message of a `must list` check never applies to it |
| S14 | Project: `kind: project` if and only if a `project` block; track `practical`; exactly one language, `python`, `typescript`, `go`, `java`, `kotlin` or `rust`; `project.entry` well formed for the language (a dotted module of identifiers in Python, a relative `.ts` path inside the root in TypeScript, a relative `.go` path inside the root that is not a `_test.go` file in Go, in Java and Kotlin the fully qualified name of a class in a named package, each part an identifier that is no keyword of either language, the last part being the signature's class, in Rust a crate name: lowercase letters, digits and `_`, not a keyword or a crate the build names); in Go, the last directory name of `project.tests` is a Go identifier; in Java and Kotlin, `project.tests` is a package directory under `src/test/java/` (`src/test/kotlin/`); in Rust, `project.tests` is `tests`; comparator `ops` with `exact`, `unordered` or `float` for every method; signature types limited to scalars, arrays and lists, with no `decimal` in TypeScript; in Java and Kotlin no result holding an array or a `decimal` inside an array or list, `unordered` on an array or list result only over `int`, `long`, `double`, `string` or `date`, and no `float` on one ([meta.yaml](problem-format.md#metayaml-1)); exactly one approach; no `generator.py`, `checker.py`, `buggy/`, `stub`, `perf`, `oracle` or `generate` cases. A project may have stress cases, a `concurrency` block whose `model` is one string valid for its language, broken overlays in `solutions/broken/` and, for a `checker` invariant, a `stress_checker.py`, and S11 and S12 apply to them ([stress cases in projects](problem-format.md#stress-cases-in-projects)) |
| S15 | Project starter: `starter/` exists, holds the entry file (`project.entry`) and `README.md`, at most 50 files and 256 KiB, UTF-8 text only, no symbolic links, no build output, caches or lock files, and no `.env` at its root, which a [service project](service-projects.md#env) gets from `project.env` ([starter](problem-format.md#starter)); Python: `pyproject.toml` with no `[project]` table, `requires-python` or `[tool.uv]`, and no top-level module or package named after a standard-library module or `pytest`; TypeScript: `package.json` with `"type": "module"` and no dependencies, and `tsconfig.json`; Go: `go.mod` with `module <slug>` and `go 1.24` (`go 1.25` in a virtual-clock project), requiring only vendored modules at their vendored versions (`github.com/shopspring/decimal v1.5.0`), each with its `replace` to `../../.cs/runtime/runners/go/third_party/<module>`, no `go.sum`, `go.work` or `go.work.sum`, and an entry file that declares a package other than `main`; Java and Kotlin: `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and `gradle/wrapper/gradle-wrapper.properties` exactly as the language's template writes them (in a problem of your own workspace, `build.gradle.kts` may also be the text of `cstudy` 0.9, whose comment names JDK 21), with the slug as `rootProject.name`, no `gradlew` or `gradlew.bat`, no `build`, `.gradle` or `.kotlin` directory and no `.class` or `.jar` file; Rust ([Rust projects](problem-format.md#rust-projects)): `src/lib.rs`, a `Cargo.toml` whose `[package]` names the crate `project.entry` with `edition = "2021"` and `rust-version = "1.80"` and no `build`, `links` or `workspace` key, with no table but `[package]`, `[dependencies]` and `[dev-dependencies]`, whose dependencies are only the vendored `rust_decimal` and `chrono` (and `tokio` in a virtual-clock project), each declared exactly as the runner declares it, and `rust_decimal` or `chrono` in `[dependencies]` when the signature uses `decimal` or `date`; a `.cargo/config.toml` holding exactly the vendored source; no `Cargo.lock`, `target/`, `build.rs`, `rust-toolchain` or `rust-toolchain.toml`. A virtual-clock starter also carries the clock pieces of its language: in Python its `pyproject.toml` loads `cs_support.virtual_clock` (`-p cs_support.virtual_clock` or `-pcs_support.virtual_clock` in pytest's `addopts`, a string or a list), in TypeScript it holds `tests/virtual-clock.ts` byte for byte as the template writes it, which is `runners/typescript/lib/virtual-clock.ts` (S15 compares its SHA-256, which a test keeps equal to the runner's file; in a problem of your own workspace, the digest of a helper that an earlier `cstudy` wrote passes too), in Kotlin its `build.gradle.kts` is the virtual-clock template's, which applies `cs.coroutines` as well as `cs.project` (no text of 0.9 passes for it), and in Rust its `Cargo.toml` declares tokio in `[dependencies]` exactly as the runner declares it (`tokio` is refused in a project on the real clock). The overlay's paths stay inside the tree and its files are UTF-8 text |
| S16 | Project: no starter file under `project.tests` has the name of a generated test file (`test_level_<n>.py`, `level-<n>.test.ts`, `level_<n>_test.go`, `Level<n>Test.java`, `Level<n>Test.kt`, `level_<n>.rs`); `problem.md` has a non-empty `## Project` section; the explanation has `### Design` |
| S17 | `jdk` ([JDK range](problem-format.md#jdk-range)): present only on a problem that lists `java` or `kotlin`. `min`, when given, is above the supported minimum (21) and at most the supported maximum (26), which caps every level. `max`, when given, is at least the effective minimum (`min`, else 21) and differs from the supported maximum (26), because an explicit 26 would keep the problem from following the range when it grows; a `max` above 26 is an opt-in and passes. When the supported range grows, S17 flags each `max` that the new range reaches. The schema (S1) holds the shape: integers, no other keys, at least one of `min` and `max` |
| S18 | Virtual clock ([project problems](problem-format.md#asynchronous-code-and-the-virtual-clock)): `async` only on methods of a project in Python, TypeScript, Kotlin or Rust, and only with `project.clock: virtual`; `project.clock: virtual` only in Go, Python, TypeScript, Kotlin or Rust, and only in a language whose runner grades it ([scope and order](../decisions/0017-async-project-problems.md#scope-and-order)). Harness operations only with the virtual clock, with valid arguments: `@advance` from 1 to 2,147,483,647 ms (Node's largest timer delay); `@spawn` a task name unique in its case and a method of the case's level or below with its arguments, an asynchronous method outside Go; `@join` a task spawned earlier and not yet joined; `@now` none. Every spawned task is joined. Expected values: `null` for `@advance` and `@spawn`, the method's result type for `@join`, an integer for `@now`. Ties are content's to avoid; no static check finds them, and D10 finds those that Go and Python shuffle |
| S19 to S23 | [Service projects](service-projects.md#static): the manifest, the mock configs, the compose file, `requires` and the HTTP cases. S14 to S16 read differently for one |
| S24 | Labels ([content](content.md#labels)): a catalog problem has `domains`, `job_roles` and `scope`, and `scope` fits `kind`: `project` or `system` for `kind: project`, `function` for any other kind. A problem in your own workspace may leave all three out, and one that names a `scope` still has to fit it. An item has the same three, with `scope: system` for a `system-design` item and `function` for a `code-review` item ([items](#items)) |
| S25 | `guides` names [concept guides](guides.md) that exist |

### Dynamic

| Id | Check |
|----|-------|
| D1 | Generated stubs compile or import in every language in `languages`. Project: the starter loads instead: a grading job of level 1 against the copied starter reports a result for every case and no `load_error` (cases may fail), and the starter's native suite runs to `job_end` without crashing the runner |
| D2 | `generator.py` is deterministic (two calls with the same seed and size are equal) and its output passes `validate` |
| D3 | Every approach file passes every case, including generated cases; progressive and project references implement every level, and each failure names its level (`level 2 ex2 FAIL: ...`). A project reference runs as the starter with its overlay ([reference](problem-format.md#reference)) |
| D4 | `--oracle`: 200 inputs (or `--oracle-cases N`) from the generator at small sizes (n drawn from 1 to 30 with seeds 1..N); every approach in every language agrees with the oracle under the comparator; for `checker` problems every output passes the checker. A problem without `generator.py` skips it and prints `oracle n/a`; the [ready criteria](#ready-criteria) still require a generator for `dsa` problems |
| D5 | `--ladder`: each approach's measured time band is consistent with its declared `time_class` ([performance-analysis](performance-analysis.md#integration)). On a busy machine the ladder is a warning, and a contradiction there is measured once more after the machine settles ([busy machine](performance-analysis.md#busy-machine)). A problem without `generator.py` skips it and prints `ladder n/a` |
| D6 | Concurrent, and projects with stress cases (the reference): every approach passes every sequential case, and every stress case in 10 of 10 runs (or `--stress N`) per variant; reports the slowest run as a share of `deadline_ms`. The languages build side by side, but their runners take turns, so each stress run has the machine to itself as a user's `cstudy test` does: run together, every language's workers competed for the cores, which hid races and stretched runs |
| D7 | Concurrent, and projects with stress cases (every broken overlay, built on the starter and the reference's overlay): every broken reference passes every sequential case, and fails each of its `caught_by` cases in at least 9 of 10 runs (`ceil(0.9 * N)`) per language and variant. Runs on every `cstudy verify` of the problem; it is the Phase 5 exit criterion |
| D8 | `stub: buggy`: in every language the buggy file builds, loads and fails at least one case (any status but `PASS`); it replaces D1's generated-stub check, and D3 still requires the fixed references to pass |
| D9 | Project: the reference passes the generated test file of every level and every test file of the starter, through the native suite ([suite job](runners.md#suite-job)): every test `ok` or `skipped`. For a virtual-clock project these are the generated virtual-clock tests, so D9 also proves that they pass natively against the reference |
| D11 | [Service projects](service-projects.md#dynamic): D1, D3 and D9 over real stacks, then the install, `bootstrap` twice in a row, three runs alike, the slowest case, the install's size and no way out of the sandbox |
| D10 | Virtual-clock project: every case gives the same outputs in 10 runs of the reference, each in a runner of its own, and the slowest run of a case stays within 25% of its hang guard (the case's `hang_guard_ms`, else `limits.hang_guard_ms`, else 10 s); outputs are compared whole, and a run that errors, deadlocks or times out is a different output. It runs after D3 on every `cstudy verify` of the problem (not with `--static`), and only when the reference loads. Go's runtime shuffles simultaneous wake-ups and Python's loop shuffles tied timers by seed (seeds 0 to 9 in D10, seed 0 in grading and in your tests, so the two agree), so a case whose expected values depend on a tie fails D10 in those languages. TypeScript's mock timers and Kotlin's test scheduler fire tied events in the order they were scheduled, so D10 cannot see a tie there, and the rule holds without a check |

D2, D4 and D5 do not apply to concurrent or project problems. Their D6, D7 and D10 runs are not part of the 30 s `cstudy verify <slug>` target in NFR-3, because they execute about 10 runs per reference, case and variant.

**JDK range.** The Java and Kotlin checks run on the JDK that the shell selects ([cli](cli.md#the-selected-jdk)). A problem whose range does not contain that JDK skips its Java and Kotlin checks with a line that names the range and the JDK (`skipped  java, kotlin: runs on JDK 24 to 26; JAVA_HOME selects JDK 21`), and `--require-ready` counts a skip as not passed. Everything built from the content (references, broken references, buggy files, generated stubs, project starters with their reference overlays) compiles at the problem's minimum release, so `cstudy verify` on any JDK of the range rejects an API or a language feature newer than the declared minimum, with no second JDK installed ([runners](runners.md#the-jdk-and-the-release-level)).

D6, D7 and the deadline margin keep their thresholds on a busy machine: relaxed there, they would pass a stress case that misses races on a user's idle one. When one of them fails while the 1-minute load average is above half the cores, or on battery, the problem gets a warning that names the condition (`stress checks failed on a busy machine (load 13.4 is above half of 11 cores): ...`), so a load flake can be told from a weak stress case. Measured with three to four other agents on 11 cores (load 10 to 17), `token-bucket-limiter` and `read-write-lock` failed 4 of 6 verifies while every language's runner ran at once (Kotlin, Rust and Python broken references caught 7 or 8 times in 10, a correct Rust run at 31% of its deadline) and 1 of 6 once the runners took turns (Python `unlocked-count` caught 8 times in 10; the slowest correct run at most 13%).

### Coverage report

`cstudy verify` always ends with per-language coverage (problems with at least one passing reference in that language over problems that list the language) and lists drafts with partial coverage. Missing languages are not failures for drafts; they are failures under `--require-ready`.

## Debugging problems

A debugging problem is an ordinary problem (`track: debugging`, `stub: buggy`) whose user file starts as working-looking code with a planted bug. It follows every rule above (statement, tests, explanation, ready criteria) plus:

- `buggy/solution.<ext>` for each language in `languages`, written like a reference file (no JVM `package` line), with the same symbols the signature declares.
- The bug makes at least one case fail in every language (D8); visible examples may pass, so the user has to find the failing input.
- `solutions/` holds the fixed code as the `optimal` approach; `explanation.md` names the bug in `### Intuition` and the general trap in `### Pitfalls and edge cases`.
- A debugging problem is graded synchronously, so a fix that needs a real `await` cannot pass one: `async` is for projects only (S18), and a Promise result is `invalid_output`. Such a bug is a project on the virtual clock whose starter holds it (`0267`).
- A language-specific bug (integer overflow, mutable default arguments, boxed equality) restricts `languages` to the languages that have it. Go and Rust get bugs of their own (append aliasing, nil map writes, `usize` underflow, NaN ordering and others), each listing only `go` or `rust`, rather than ports of the core-language problems ([ADR 0012](../decisions/0012-go-and-rust.md)).

## Items

System design and code review items (`tracks/<track>/<slug>/`, format in [content](content.md#non-autograded-item-format)) run no code: `cstudy verify` applies static checks only, under the same flags (`--track`, `--static`, `--require-ready`), and items do not count towards the coverage report.

| Id | Check |
|----|-------|
| I1 | `item.yaml` valid against `schemas/item.schema.json` |
| I2 | The directory name equals `slug` and its parent equals `track`; slugs unique across `problems/` and `tracks/` |
| I3 | `prompt.md`: `# <title>`, the track's required sections, non-empty and in order, no `TODO` |
| I4 | `rubric.md`: `# <title>: Rubric`, at least one `##` area, every area with a `- [ ] <criterion>` line, no `TODO` |
| I5 | `reference.md`: `# <title>: Reference`; system design: required sections, non-empty and in order; code review: severity sections only, in order, each listing `- ` issues; no `TODO` |
| I6 | `template.md`: `# <title>: Notes` and at least one `##` section |
| I7 | Code review: exactly one of `change.diff` (not empty) or `files/`; other tracks: neither |
| S24 | `item.yaml` has `domains`, `job_roles` and `scope`, and `scope` is `system` for a `system-design` item and `function` for a `code-review` item ([content](content.md#labels)) |

`related` slugs that name no problem or item are warnings. `status: ready` additionally requires, for system design, at least one reference: a `references.links` or a `references.study_guides` entry. Study-guide paths are relative to the user's study-guides root ([study guides](content.md#study-guides)); `cstudy verify` checks their form, not that the files exist.

### Item workflow

| Step | Action | Check |
|------|--------|-------|
| 1 | Create `tracks/<track>/<slug>/` with `item.yaml` (`status: draft`, and the [labels](content.md#labels)) | `cstudy verify <slug> --static` |
| 2 | Write `prompt.md`, then `reference.md` | `--static` |
| 3 | Write `rubric.md` from the reference: one criterion per point a strong answer makes | `--static` |
| 4 | Write `template.md` with the reference's sections | `--static` |
| 5 | Link public sources in `references.links` and, optionally, study-guide sections in `references.study_guides`; set `status: ready` | `cstudy verify <slug> --require-ready` |

## Guides and paths

[Concept guides and learning paths](guides.md) run no code in `cstudy verify`: it applies their static checks, G1 to G10 and P1 to P5, when it verifies the whole catalog, and they do not count towards the coverage report. Their examples run in a content test instead ([examples](guides.md#examples)). [Writing a guide](guides.md#writing-a-guide) lists the steps.

## Quality gate

| Content | Gate before merge |
|---------|-------------------|
| Catalog batches (Phases 1 and 3 on) | `cstudy verify --changed --oracle --require-ready` exits 0; from Phase 2 on also `--ladder` |
| Runner or codegen changes | `cstudy verify --conformance` plus full `cstudy verify` |
| Concurrency batch (Phase 5) | `cstudy verify --changed --require-ready` exits 0, after `cstudy verify --conformance` passes with the stress fixtures |
| User drafts | `cstudy verify <slug>` exits 0 |

A `pre-push` hook that runs the catalog gate is recommended but not mandatory ([contributing](../../CONTRIBUTING.md#checks)).

## Authoring checklist

- [ ] Statement, examples and tests are original ([copyright policy](content.md#copyright-policy)); `references.leetcode` links the original.
- [ ] `problem.md` has every required section; each visible case has an explained example.
- [ ] Hidden cases cover: minimum size, single element, duplicates, negatives and zero, all-equal values, sorted and reverse-sorted input, maximum values, and the no-answer path when the problem has one.
- [ ] Comparator chosen deliberately: `unordered` or `checker` whenever several outputs are valid.
- [ ] Brute-force oracle in Python; generator deterministic and constraint-valid.
- [ ] Every approach in every listed language, Go and Rust included, written idiomatically (not transliterated); a concurrency or debugging approach without a counterpart in some language names its `languages` and says why in its language notes.
- [ ] Explanation section for every approach with all required subsections; language notes where idioms differ.
- [ ] `perf.size_ladder` within constraints; a `generate` case at the largest size.
- [ ] The ladder spans two or more decades where the slowest approach allows it (over one decade, neighbouring classes such as n^1.5 and n^2 are within the [drift tolerance](performance-analysis.md#ladder-check)), and the generator drives every approach to its declared worst case at every size: the same input family at every seed, no early exits that some seeds hit and others miss.
- [ ] A property the generator draws per seed (the number of distinct letters, the share of duplicates) must not change what a library does per element: a sort is much cheaper on 3 distinct letters than on 26, so a ladder with one such input shows a step, not the declared class (`valid-anagram`). Draw the property once for the whole ladder range, and start the ladder below a library's algorithm switch when a language has one (Java sorts a `char[]` by counting above 1750 elements).
- [ ] A search that stops at its first success (`word-search`) gets inputs at the ladder sizes that it must search to the end, or to a fixed share of it, in every approach: random inputs make the time at each size depend on the input drawn, and in Go and Rust such calls take under a microsecond, where the ladder cannot see growth.
- [ ] `time_class` is the class with the libraries the references use: re-sorting a list that is sorted but for a few values is a linear pass with every library sort in the catalog (Timsort in Python, TypeScript and Kotlin's lists, run merging in Java's `Arrays.sort`, Rust's driftsort, Go's pdqsort), so such a brute force is O(n) per sort, not O(n log n) (`last-stone-weight`).
- [ ] A lower-order term that grows with n, such as a fixed cost per round of a simulation, is not the fixed per-call cost the drift allows for: when it dominates the smallest size in Go or Rust, start the ladder above that size instead of declaring a lower class.
- [ ] `cstudy verify <slug> --oracle --ladder --require-ready` exits 0.

### Virtual-clock checklist

- [ ] Every wait ends at a virtual time that the expected values fix, and every task the code starts can be stopped through its API before a case ends. Every `@spawn` has its `@join`.
- [ ] No expected value depends on the order of events due at the same virtual instant: two timers that fire together, a retry and a timeout that expire together. Go and Python shuffle them, so D10 fails there; TypeScript and Kotlin keep the order they were scheduled in, so only the author sees the tie.
- [ ] Expected values are durations from the start of the case, read with `@now` or returned by the code, never a reading of the clock: each language's clock starts at its own epoch.
- [ ] The code reads time only through the clock the language's facility controls (Go's `time` package, `loop.time()`, `Date.now()`, the coroutine scheduler's time, tokio's `Instant`) and waits on nothing the clock cannot see: no thread, no lock whose holder waits, no real I/O. Such a wait never lets time move and meets the hang guard as `timeout`.
- [ ] `limits.hang_guard_ms` is a few seconds. A correct case takes milliseconds, and D10 keeps the slowest run under 25% of the guard.
- [ ] A stress case sits at the level whose statement first shares the instance between threads or tasks, calls methods of its level and below that wait on no timer, and leaves the level with at least 2 visible and 2 hidden sequential cases.

### Concurrency checklist

- [ ] `## Concurrency` states which methods run concurrently, which block and until when, and the ordering guarantee.
- [ ] Languages chosen by model: TypeScript only when the race is visible across `await` points; Python's model chosen deliberately (`threads` or `async`); Kotlin and Java always `threads`.
- [ ] Sequential cases never block (no `take` on an empty queue, no `acquire` beyond the permits).
- [ ] Every invariant holds on every schedule of a correct implementation; `min_occupancy` only with a `@pause` in the section.
- [ ] Values are traceable: producers use `$seq` with a `worker_stride` larger than any `repeat`, so multisets, `distinct` and `source_order` can name the lost or duplicated value.
- [ ] Contention is real: several workers per group, small capacities or few keys (`$rand` over a small range), and a `@pause` inside probe sections.
- [ ] Python broken references target a pattern observable at their `python_granularity` ([table](problem-format.md#observable-races-in-python)); `instruction` granularity comes with a lower Python `repeat`.
- [ ] Go broken references race only on single-word fields (`int`, `bool`, pointers): a concurrent map write is a fatal error that crashes the runner, and a torn slice, string or interface header corrupts memory. Use `sync.Map` or atomics where a map or a growing slice is involved.
- [ ] Rust broken references are logic races, since safe Rust has no data races: two lock acquisitions where one is needed, `if` instead of `while` around `Condvar::wait`, a lock-order deadlock, or a separate atomic load and store. A bug that safe Rust cannot express (an unguarded linked list, mutation under a read guard) gets `languages` without `rust`, and Rust gets a broken reference of its own.
- [ ] A broken reference fails in more than one way where it can: one whose only failure is a window of a few instructions, such as a check and an increment on lossless atomics, is caught fewer than 9 times in 10 on a busy machine. Losing updates, as a `volatile` counter on the JVM does, widens it.
- [ ] One broken reference per bug class, each with a `caught_by` case designed for it: missing lock, `if` instead of `while`, wrong notify, lock-order deadlock (caught as `STALLED`).
- [ ] Correct references pass 10 of 10 runs per variant, with the slowest run under 25% of `deadline_ms`; broken references fail at least 9 of 10.
- [ ] Explanation: `### Language notes` covers each language's primitives and the Kotlin coroutine version; each broken reference has `### Bug`, `### Failing interleaving` and `### Fix`.
