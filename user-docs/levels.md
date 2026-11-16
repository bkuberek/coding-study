---
title: Progressive levels and projects
summary: Problems that grow over several levels, project folders graded with cstudy submit, and how a pass through some of the levels counts.
section: Practice
order: 60
---

# Progressive levels and projects

Some problems grow, as work does: you build a first version, then a new requirement arrives, then another. Each step is a **level**. You see only the levels you have opened, and passing one opens the next.

| Kind | You write | Levels open with |
|------|-----------|------------------|
| Progressive | One file, as for any problem | `cstudy test`, when a run passes every case of the open levels |
| Project | A folder of several files, with tests you run in your language's own tool | `cstudy submit`, which grades every open level |

## Progressive problems

Start one as any problem. Its statement shows level 1; `cstudy test` runs the cases of the levels you have opened, and a run that passes all of them opens the next level and rewrites the statement:

```text
$ cstudy test
level-store · python · level 1 of 3 · 4 cases (1 visible, 3 hidden, 0 generated)

PASS     ex1   0.02ms
PASS     3 hidden cases

4/4 passed · total 0.3s
level 1 passed · unlocked level 2 of 3: Remove and size
statement  .statements/level-store.md (updated)
```

`--level N` runs only levels 1 to N, which helps when a change for a new level breaks an old one:

```bash
cstudy test --level 1
cstudy show level-store --level 2      # the statement up to level 2, once it is open
```

## Project problems

A project problem is a small codebase in one language. `cstudy start` copies its starter files to `projects/<slug>/` and writes the tests of level 1 in your language's test framework, so your IDE runs them as it runs any test:

```text
bank-project-python · hard · practical · python · project
project    projects/bank-project-python (6 files)
entry      bank/bank.py: Bank
tests      tests/test_level_1.py (2 tests)
statement  .statements/bank-project-python.md
level      1 of 4: Accounts and transfers
next       cstudy test --watch, then cstudy submit
```

| Command | Does |
|---------|------|
| `cstudy test` | Runs the project's own tests: the generated ones of each open level, the starter's and yours. It is feedback, and opens nothing |
| `cstudy submit` | Grades every case of every open level, visible and hidden. A submission that passes all of them opens the next level and writes its tests |
| `cstudy status` | Lists the folder's files, each `unchanged`, `modified`, `added` or `deleted` |

```text
$ cstudy submit
bank-project-python · python · submit levels 1-2 of 4 · timer 33:05 / 90:00

level 1  PASS     5/5 (2 visible, 3 hidden)
level 2  FAIL     4/5 (2 visible, 3 hidden)

9/10 passed · level 3 opens when levels 1-2 pass
```

Add files, rename them and write tests of your own: the folder is yours. To get one starter file or generated test file back as `cstudy` provides it:

```bash
cstudy start bank-project-python --restore tests/test_level_2.py
```

Hints open with the levels: a hint about level 3 waits until level 3 is open.

## When you finish

You do not need every level to finish an attempt. Once level 1 passes, `cstudy done` takes a rating, and the attempt passes through the highest level you passed:

```text
level-store · python · passed · through level 2 of 3 · 18m 40s · rating ok · hints 0
```

For a progressive problem that is the latest test run; for a project, the latest submission that graded every open level. The review comes back on its normal schedule, and starts at level 1 again. The next attempt shows what you reached, such as `last time: through level 2 of 4; try level 3`.

Each level is mastered on its own reviews, so a problem can read `mastered through level 2 of 4`: you recall the first two levels well, and the later ones are still new.

A mock interview keeps a stricter rule: there, an attempt passes only with every level ([mock interviews](planning.md#mock-interviews)).

## Aim at a level

A set or a learning path can aim lower than the last level. `cstudy set add <set> <slug> --level 2` counts the entry once you pass level 2 ([problem sets](planning.md#problem-sets)), and a path's step can do the same.

## Service projects

A service project is a project that runs a real app in Docker, with mock servers for the services it calls, and is graded over HTTP. It has levels too, opened by `cstudy submit`. [Service projects and the dev stack](service-projects.md) covers them.
