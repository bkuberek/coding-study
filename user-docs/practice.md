---
title: Work on a problem
summary: The practice loop from start to done, with tests, hints, solutions, benchmarks and how each attempt is graded and scheduled.
section: Practice
order: 50
---

# Work on a problem

Each time you work on a problem is an **attempt**. You start it, write and test your code, and finish it with how it went; `cstudy` then schedules the problem's next review. The loop is the same in the terminal, your IDE and the web UI, and the [command reference](commands.md) lists every flag.

```bash
cstudy start two-sum --lang python
cstudy test --watch
cstudy hint                     # only if you are stuck
cstudy done --rating ok
```

## Find a problem

```bash
cstudy next                     # what to do now: an open attempt, a due review, or a new problem
cstudy list --track dsa --difficulty easy
cstudy list --search anagram
cstudy show two-sum             # print the statement, without hints
```

`cstudy list` takes filters such as `--track`, `--pattern`, `--difficulty`, `--status`, `--lang`, `--domain`, `--role` and `--scope`, `--checked-by tests` or `--checked-by rubric` for how a problem is checked, and `--json` for scripts. A problem's **slug**, such as `two-sum`, names it in every command; `--json` also gives it as an **id**, `problem/two-sum`, which is for scripts and never typed. [Kinds of problems](problem-kinds.md) explains the tracks, the kinds and the labels, and [plan your practice](planning.md) covers `cstudy next` and sets.

## Start

```bash
cstudy start two-sum                    # in your default language
cstudy start two-sum --lang kotlin
cstudy start two-sum --timer 25m        # a time box
```

`cstudy start` writes a stub for your code, renders the statement into `.statements/`, opens both in your editor, and begins the attempt. It prints where each file is:

```text
two-sum · easy · arrays-hashing · kotlin
stub       jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt
statement  .statements/two-sum.md
next       cstudy test --watch
```

| Flag | Does |
|------|------|
| `--lang` | The language; without it, `default_lang` from your [configuration](settings.md#your-configuration), Python unless you change it |
| `--timer` | A time box, such as `25m` or `1h`. `cstudy test` shows the time left, and finishing over it caps the grade at `hard` |
| `--fresh` | Moves your earlier file to `.archive/` and writes a new stub |
| `--no-open` | Does not open your editor |

Starting a problem you already have open in that language resumes it. A review always starts from a new stub, and the earlier file moves to `.archive/`, where the web UI's history reads it. Nothing is ever deleted.

Most commands that take a slug can take your solution file instead, or nothing at all for the attempt you used last: `cstudy test`, `cstudy hint` and `cstudy done` act on it.

## Test

```bash
cstudy test                     # run every case once
cstudy test --watch             # run again on every save
cstudy test --case ex1          # only this case
cstudy test --all               # print the passing hidden cases too
```

Each case is `PASS`, `FAIL`, `ERROR`, `TIMEOUT` or `TLE`. Visible cases always show; passing hidden cases collapse into a count, and a failing one shows its input, the expected answer and yours. On a full pass the last line says what to do next:

```text
14/14 passed · total 0.9s
all passed. Next: cstudy done --rating easy|ok|hard
```

| Flag | Does |
|------|------|
| `--time-limit` | Turns on time limits: the problem's own, or a factor of the reference (`--time-limit=5x`) or a duration (`--time-limit=1500ms`). The value comes after `=` only |
| `--perf` | After every case passes, runs a short benchmark and prints its verdict |
| `--typecheck` | TypeScript: also runs the type checker, since running TypeScript does not check types |
| `--json` | One JSON document instead of the report, for scripts |
| `--debug` | Waits for your IDE's debugger to attach, with time limits off ([debug a run](ide-and-debugging.md#debug-a-run)) |

## Hints and solutions

```bash
cstudy hint                     # the next hint
cstudy solution two-sum         # the reference solution with its explanation
cstudy solution two-sum --all   # every approach
```

A problem has a few hints, shown one at a time. Any hint caps the attempt's grade at `ok`, so the review comes back a little sooner.

`cstudy solution` shows the explanation and the reference code in your language, or another with `--lang`. While you have an unsolved attempt open, it asks first, since a solution seen before a pass grades the attempt `again`; `--yes` skips the question. `--explanation-only` leaves the code out.

## Measure your solution

Passing the tests says your code is right. `cstudy bench` says whether it is fast enough: it runs your solution at growing input sizes, fits how its time grows, and compares it with the reference approaches.

```bash
cstudy bench                    # your solution and the references
cstudy bench --refs-only        # the references only
```

It prints a verdict, `optimal`, `near-optimal` or `suboptimal`, with how confident it is. With the default settings, a `suboptimal` verdict at medium or high confidence caps the grade at `hard`.

## Finish

When the tests pass, finish the attempt with how hard it felt:

```bash
cstudy done --rating easy       # or ok, or hard
cstudy done --gave-up           # when it never passed
cstudy done --rating ok --notes "forgot the empty input"
```

```text
two-sum · kotlin · passed · 18m 40s · rating ok · hints 0
next review  2026-10-27 (in 3 days) · ease 2.50
```

`cstudy done` grades the latest test run. A rating needs a run where every case passed; otherwise use `--gave-up`.

### How the grade is set

| Grade | When |
|-------|------|
| `again` | You gave up, or saw the solution before your first pass |
| `easy`, `ok`, `hard` | Your rating, then capped: any hint caps it at `ok`; finishing over the timer, or a `suboptimal` benchmark, caps it at `hard` |

The grade sets when the problem comes back. A first `ok` brings it back in 3 days, the next in 7, then further apart each time; `again` brings it back tomorrow, and `easy` waits longer. A problem whose review interval reaches 21 days counts as **mastered**. You can change these intervals in your [configuration](settings.md#your-configuration).

## Stop without finishing

```bash
cstudy abort                    # asks first; --yes does not
```

`cstudy abort` ends the attempt as abandoned. Your files stay, and your progress and review schedule do not change; the next `cstudy start` of that problem begins a new attempt in the same file.

## See where you stand

```bash
cstudy status                   # the attempt: time, hints, the latest run
cstudy history two-sum          # every attempt, run and review of a problem
cstudy stats                    # your progress by pattern
```

## System design and code review

System design and code review problems are graded by you, against a rubric: `cstudy list --kind system-design` and `--kind code-review` list them. `cstudy start url-shortener` writes a notes file in `notes/<track>/<slug>.md` from the problem's template and renders the prompt, with the change to review for code review, to `.statements/<slug>.md`. Answer in the notes, then compare with the reference:

| Step | Command | Effect |
|------|---------|--------|
| 1 | `cstudy next --track system-design` | Picks a due or new problem |
| 2 | `cstudy start <slug>` | Writes the notes file and the prompt; time box it with `--timer 45m` |
| 3 | Answer in the notes file | System design: requirements, estimates, API, data model, high-level design, deep dives, trade-offs. Code review: issues by severity, each with its location and the change you would ask for |
| 4 | `cstudy solution <slug>` | Shows the rubric, then the reference answer, or the issues a strong reviewer finds |
| 5 | `cstudy done <slug> --rating easy\|ok\|hard` | Self-graded; schedules the next review |

```bash
cstudy start url-shortener
cstudy solution url-shortener   # the rubric and the reference
cstudy done --rating ok
```

Here the rating is the whole grade: seeing the reference, hints and the timer never lower it. Behavioral rounds have no problems: prepare from your own story bank, kept with your other notes and outside the catalog.
