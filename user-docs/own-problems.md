---
title: Write your own problems
summary: Scaffold a problem of your own with cstudy new, check it with cstudy verify, take it from draft to ready, step by step, and fix folders from older versions.
section: Practice
order: 95
---

# Write your own problems

A problem of your own lives in your workspace's `problems/` folder, in the same format as the catalog's. It joins the catalog for every command: `cstudy list` shows it after the catalog's problems, and you start, test and finish it as any other.

```bash
cstudy new max-gap --from-template array
cstudy verify max-gap --static
cstudy start max-gap
```

## Create one

`cstudy new` writes `problems/<slug>/` in your workspace from a template, with `status: draft`. It prints `created  problems/max-gap  (array template, draft)`, then the next steps, from writing the statement to setting `status: ready`, each with the check to run after it.

The slug names the problem in every command and never changes: your progress is kept by it. It is lowercase letters, digits and single hyphens, a letter first. The template sets the problem's shape:

| Template | You get | Track |
|----------|---------|-------|
| `array`, the default | A function that takes a list of integers and an integer, and returns an integer | `dsa`, pattern `arrays-hashing` |
| `tree` | A function that takes a binary tree and returns one | `dsa`, pattern `trees` |
| `design` | A class with a constructor and two methods, tested by sequences of calls | `dsa`, pattern `arrays-hashing` |
| `progressive` | A class that grows over levels, one method per level | `practical` |
| `concurrent` | A class whose methods several threads call at once, with a sequential case, a stress case and a broken reference | `concurrency` |
| `project-python`, `project-typescript`, `project-java`, `project-kotlin`, `project-go`, `project-rust` | A project in that language: a starter folder, two levels, and the reference as files over the starter | `practical` |
| `project-python-service`, `project-typescript-service`, `project-java-service`, `project-kotlin-service`, `project-go-service` | A service project in that language, graded over HTTP in a sandbox, which needs Docker ([service projects](service-projects.md)) | `practical` |

| Flag | Does |
|------|------|
| `--from-template <template>` | The template, from the table above |
| `--track <track>` | The track, instead of the template's: `dsa`, `practical`, `lld`, `concurrency` or `debugging`. A `dsa` problem needs a primary pattern; `lld` also writes `rubric.md` |
| `--title <title>` | The title; without it, made from the slug: `max-gap` is `Max Gap` |
| `--difficulty <difficulty>` | `easy`, `medium` or `hard`; `medium` without it |
| `--pattern <pattern>` | The primary pattern, instead of the template's |
| `--virtual-clock` | A project template's variant for code that waits, tested on a virtual clock instead of the real one. Not every language has it, and `cstudy new` says so |
| `--stress` | A project template's variant for code that several threads or tasks share, with a stress case and a broken version to catch |

`cstudy new` refuses, with exit 3, a slug that the catalog or your own problems already use, and an invalid slug, track, pattern or title.

| Variant | Templates |
|---------|-----------|
| `--virtual-clock` | `project-go`, `project-python`, `project-typescript`, `project-kotlin` and `project-rust`. Java has no virtual clock |
| `--stress` | Every `project-*` template but the service ones. `project-typescript` takes it only with `--virtual-clock`, since its methods are asynchronous |

### Cases on the virtual clock

A project on the virtual clock (`project.clock: virtual` in `meta.yaml`) grades code that sleeps, sets timers, times out and retries, without waiting: time moves only when every task of your code waits. A method marked `async: true` returns the language's awaitable, in Python, TypeScript, Kotlin and Rust. Besides your methods, a case's `ops` in `tests.json` can hold four harness operations, which begin with `@`:

| Operation | Arguments | Expected value | Does |
|-----------|-----------|----------------|------|
| `@advance` | `[ms]` | `null` | Moves the clock forward by `ms` milliseconds, firing each timer due on the way |
| `@spawn` | `[task, method, ...arguments]` | `null` | Starts a call without waiting for it, as the task named `task`. Outside Go the method is `async: true` |
| `@join` | `[task]` | The method's result | Waits for a task that `@spawn` started; the clock moves while every task waits |
| `@now` | `[]` | An integer | The virtual milliseconds since the case started |

The variant's second example uses all four:

```json
{"id": "ex2", "visible": true, "level": 2,
 "note": "a wait that a put ends, then a wait that times out",
 "ops": ["Mailbox", "@spawn", "@advance", "put", "@join", "@now", "waitFor", "@now"],
 "args": [[], ["w1", "waitFor", "a", 5000], [1000], ["a", "x"], ["w1"], [], ["b", 2000], []],
 "expected": [null, null, null, "", "x", 1000, "", 3000]}
```

| Rule | Detail |
|------|--------|
| Tasks | Each task name is unique in its case, and every task that `@spawn` starts is joined with `@join` |
| Methods | `@spawn` calls a method of the case's level or below, with that method's arguments |
| Ties | No expected value may depend on the order of events due at the same instant: the languages do not keep that order |
| Durations | An expected time is a duration from the start of the case, as `@now` reads it, never a reading of a clock |
| Deadlocks | A case that waits while nothing can run ends at once as `stalled`, with the operation and the virtual time |
| The check | `cstudy verify` runs every case several times and reports `clock 10/10`, the fewest runs that agreed on every output; a case whose outputs differ between runs is listed under `clock:` |

A stress case runs on the real clock, so in a project on the virtual clock its steps call only methods that wait on no timer.

## The files

```text
problems/max-gap/
  meta.yaml            the title, difficulty, track, signature, comparator, approaches, labels and status
  problem.md           the statement: input, output, constraints, examples and hints
  tests.json           the cases, visible and hidden
  generator.py         random inputs, for the oracle and the ladder
  solutions/
    explanation.md     one section per approach
    <approach>.<ext>   a reference per approach and language
```

| File | What to know |
|------|--------------|
| `meta.yaml` | `languages` lists the languages to write references in. `cstudy new` writes the line; remove the languages you do not practice, with their reference files. Without the line, a problem of yours lists Python, TypeScript, Java and Kotlin |
| `problem.md` | The statement, in your own words, with its hints, which `cstudy hint` shows one at a time |
| `tests.json` | Visible cases show in every run; hidden cases show only when they fail. Each case is checked against the signature in `meta.yaml` |
| `solutions/` | The reference code, which `cstudy solution` shows, and its explanation |
| `starter/` | A project template's starter, which `cstudy start` copies into `projects/<slug>/`. The reference is in `solutions/reference/`, as the files that differ from the starter |
| `solutions/broken/` | A concurrent problem's broken references, each caught by a stress case |
| `buggy/` | A debugging problem's starting code, one file per language, with the bug in it |
| `rubric.md` | An `lld` problem's design criteria and reference design |

### More fields of meta.yaml

Two optional fields of `meta.yaml` are worth knowing when you write a problem:

| Field | Does |
|-------|------|
| `jdk` | The JDK releases that the problem's Java and Kotlin code runs on: `jdk: {min: 24}` for code that needs a feature of JDK 24, `jdk: {max: 23}` for a problem that does not hold above JDK 23, or both. A bound you leave out is that of the range `cstudy` supports, 21 to 26, so leave `jdk` out unless the code needs it. `min` is above 21 and at most 26; `max` is at least the minimum and is never 26 itself, so that the problem follows the range when it grows. Only for a problem that lists `java` or `kotlin`. `cstudy verify` builds the references at the release `min` names, and the commands treat a JDK outside the range as [the selected JDK](commands.md#the-selected-jdk) says |
| `summary` | One sentence of 1 to 240 characters that the comment at the top of a new starter file shows, instead of the opening of the statement. Write one when that opening reads badly there, or gives away the approach. It says what the problem asks, never how to solve it |

## Check it

`cstudy verify` checks a problem the way the catalog's are checked. Run it after each step, starting with the quickest check:

```bash
cstudy verify max-gap --static        # the files only: nothing runs
cstudy verify max-gap                 # also every reference, in each language, against the cases
cstudy verify max-gap --oracle        # also every approach against the oracle, on random inputs
cstudy verify max-gap --ladder        # also how each reference's time grows with the input
cstudy verify max-gap --oracle --ladder --require-ready
```

| Flag | Checks |
|------|--------|
| `--static` | The schema of `meta.yaml` and `tests.json`, the statement's sections, the explanation's, the signature, and each case against the signature. No code runs |
| `--oracle` | Every approach against the oracle, a simple approach marked `oracle: true`, on inputs from `generator.py`. Without `generator.py` it says `oracle n/a` |
| `--ladder` | Each reference at growing input sizes, against the time class `meta.yaml` declares. Without `generator.py` it says `ladder n/a` |
| `--require-ready` | Fails the problem unless its `status` is `ready` and it meets what `ready` needs |
| `--oracle-cases <n>` | How many random inputs `--oracle` checks; 200 without it |
| `--lang <language>` | Only that language |
| `--track <track>` | Only the problems of that track |
| `--jobs <n>` | How many language runners work at once; one per language without it. The runners of a concurrent problem still take turns for their stress cases |
| `--skip-lang <language>` | Leaves that language out, as if the problem did not list it; repeat it for more. `--lang` and `--skip-lang` with the same language is an error |
| `--stress <n>` | The runs of each stress case, for a concurrent problem or a project with stress cases; 10 without it |
| `--changed` | The problems whose files changed from git's `main`, in a checkout of the `cstudy` source, for content you write there. It takes no slugs |

Without slugs, `cstudy verify` checks every problem, the catalog's and yours.

A language whose toolchain is not installed, such as Rust without `cargo`, is skipped, not fatal: its line says `rs skipped`, a `skipped` line gives the reason (`skipped  rust: cargo was not found on PATH`), and every other language is still checked. A service project runs in Docker, so only its Docker toolchains count, not the host's. A skip does not fail the run, except under `--require-ready`, which counts the language as not passed. A language that you leave out with `--skip-lang` is not counted at all, so `cstudy verify --require-ready --skip-lang rust` passes on a machine without Rust when the other languages pass.

### Exit codes

| Code | Means |
|-----:|-------|
| 0 | Every problem it checked passed, or `--changed` found no changed problem |
| 1 | A problem failed a check beyond the static ones: a reference on a case, the oracle, the ladder, a stress case, or what `ready` needs with `--require-ready`, which also fails on a language skipped for a missing toolchain, or a reference runner that fails to start, which fails that problem and does not stop the run |
| 3 | The command was wrong: a slug that does not exist, `--changed` with slugs or `--conformance`, or `--lang` and `--skip-lang` with the same language |
| 4 | Something on your machine is missing, such as git, or a `main` branch to compare with for `--changed` |
| 5 | Every problem that failed, failed its static checks: a file, the schema, a section, or a case that does not fit the signature |

## From draft to ready

A draft is a problem you can practice: `cstudy start`, `cstudy test` and the rest work on it. `cstudy next` skips drafts, and `cstudy list --content draft` lists them.

A problem is ready when it is complete: an optimal reference in every language it lists, enough visible and hidden cases, an explanation of every approach, and, for a `dsa` problem, a slower approach, an oracle and `generator.py`. Set `status: ready` in its `meta.yaml`, then run `cstudy verify <slug> --oracle --ladder --require-ready`. When it passes, the problem is ready, and `cstudy next` can pick it.

You can keep a problem a draft as long as you like, with references in only some languages. Time limits by factor, such as `--time-limit=5x`, need an optimal reference in the language you test.

### What ready needs

`cstudy verify --require-ready` fails a problem until it meets every row that applies to it:

| Problem | `ready` needs |
|---------|---------------|
| Every problem | `status: ready`, every check of `cstudy verify` passing, an `optimal` approach with a reference in every language of `languages`, and a reference of every approach in each of its languages |
| Function, design, progressive and project | At least 2 visible cases and 8 hidden hand-written ones |
| The `dsa` track | At least 2 approaches, a slower one or another optimal technique; an approach marked `oracle: true` in Python; `generator.py`; and a `generate` case at the largest size of the ladder, which any problem with `generator.py` needs too |
| Progressive | At least 2 levels, each with at least 1 visible case and 2 hidden hand-written ones |
| Project | The progressive rules, with at least 2 visible cases per level, and the project's own test suite passing. On the virtual clock, every case gives the same outputs in every run. With stress cases, at least 2 of them and a broken overlay, each overlay caught |
| Service project | The project rules, checked on a running Docker: without one, `--require-ready` counts the problem as not passed |
| Concurrent | At least 2 visible and 4 hidden sequential cases, at least 2 stress cases, a broken reference in every language it lists, each caught by its stress cases, and the slowest correct run of each stress case within a quarter of its deadline |
| Java and Kotlin | The selected JDK in the problem's range: a language skipped for its JDK counts as not passed |

### Step by step

`cstudy new` prints these steps for every template but the project ones, each with the check to run after it:

| Step | Do | Then run |
|-----:|----|----------|
| 1 | `cstudy new max-gap --from-template array` | |
| 2 | Write `problem.md`: the statement, input, output and constraints, in your own words | `cstudy verify max-gap --static` |
| 3 | Set `signature` and `comparator` in `meta.yaml`, and fit the labels to the problem | `cstudy verify max-gap --static` |
| 4 | Add visible examples to `tests.json`, with their explanations in `problem.md`, then hidden edge cases | `cstudy verify max-gap --static` |
| 5 | Write the brute-force approach in Python, with `oracle: true` | `cstudy verify max-gap` |
| 6 | Write `generator.py`, with its `validate` | `cstudy verify max-gap --oracle` |
| 7 | Write the optimal approaches: Python first, then the other languages of `languages` | `cstudy verify max-gap --oracle` |
| 8 | Write `solutions/explanation.md`, one section per approach | `cstudy verify max-gap --static` |
| 9 | Add the `perf` block, and `generate` cases at the largest size of the ladder | `cstudy verify max-gap --ladder` |
| 10 | Set `status: ready` | `cstudy verify max-gap --oracle --ladder --require-ready` |

A project template prints a shorter list of its own: the statement and the cases, the starter, the reference overlay level by level, then the explanation and `status: ready`, checked with `cstudy verify <slug> --require-ready`. With `--virtual-clock` it adds a step to make every case give the same outputs in every run, and with `--stress` a step to write the broken overlays and tune the stress cases until each overlay is caught.

## Labels

Three labels say what a problem is about, who it is for and how big the thing you work on is ([labels](problem-kinds.md#labels)):

| Label | Field | Template default |
|-------|-------|------------------|
| Domain | `domains` | `algorithms` for `array`, `tree` and `design`; `backend` for the others |
| Role | `job_roles` | `general` for `array`, `tree` and `design`; `backend` for the others, and `platform` too for `concurrent` |
| Scope | `scope` | `function`; `project` for the project templates |

Edit them in `meta.yaml` to fit the problem. They are optional for your own problems: one without them shows `-` in `cstudy list`, and the `--domain`, `--role` and `--scope` filters leave it out. A scope you set has to fit the kind: `function` for a function, design, progressive or concurrent problem, and `project` or `system` for a project.

## When a slug is taken

A problem of yours with the slug of a catalog problem wins: it hides the catalog's everywhere, in `cstudy list`, `cstudy start`, `cstudy verify`, `cstudy status`, `cstudy history` and the web UI, and nothing of the two is merged. Your practice files and progress therefore always belong to the problem you wrote, even after an upgrade adds a catalog problem with your slug.

`cstudy new` never takes a slug that is in use, so this happens when a newer `cstudy` adds one, or when you copy a folder in by hand. To practice the catalog's problem, give yours another slug: rename its folder and change `slug` in its `meta.yaml` to match.

Your own problems are checked by tests. A folder of yours with a `system-design` or `code-review` kind is an error, which `cstudy list` and `cstudy verify` report: `rubric problems are catalog-only`.

## Folders from older versions

Older versions of `cstudy new` named a folder `NNNN-<slug>`, such as `problems/0042-max-gap`, and wrote an `id:` line in its `meta.yaml`. Neither loads as a problem now. `cstudy verify` fails on such a folder and `cstudy doctor` warns on its `workspace files` row, and both print what to do, from the workspace root:

| The folder | The fix they print |
|------------|--------------------|
| Named `NNNN-<slug>` | Rename it to its slug, then delete the `id:` line of its `meta.yaml` |
| Named by its slug, with an `id:` line | Delete the `id:` line |
| Its slug is already another folder's | Give it a slug that is free |
| No slug to take | Give it a slug |

For `problems/0042-max-gap`:

```bash
mv problems/0042-max-gap problems/max-gap
# then delete the id: line of problems/max-gap/meta.yaml
cstudy verify max-gap --static
```

Nothing is renamed for you: the folder stays as it is until you fix it.
