---
title: Write your own problems
summary: Scaffold a problem of your own with cstudy new, check it with cstudy verify, take it from draft to ready, and fix folders from older versions.
section: Practise
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
| `meta.yaml` | `languages` lists the languages to write references in. `cstudy new` writes the line; remove the languages you do not practise, with their reference files. Without the line, a problem of yours lists Python, TypeScript, Java and Kotlin |
| `problem.md` | The statement, in your own words, with its hints, which `cstudy hint` shows one at a time |
| `tests.json` | Visible cases show in every run; hidden cases show only when they fail. Each case is checked against the signature in `meta.yaml` |
| `solutions/` | The reference code, which `cstudy solution` shows, and its explanation |
| `starter/` | A project template's starter, which `cstudy start` copies into `projects/<slug>/`. The reference is in `solutions/reference/`, as the files that differ from the starter |
| `solutions/broken/` | A concurrent problem's broken references, each caught by a stress case |
| `buggy/` | A debugging problem's starting code, one file per language, with the bug in it |
| `rubric.md` | An `lld` problem's design criteria and reference design |

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
| `--lang <language>` | Only that language |
| `--stress <n>` | A concurrent problem's stress cases, run n times each |

## From draft to ready

A draft is a problem you can practise: `cstudy start`, `cstudy test` and the rest work on it. `cstudy next` skips drafts, and `cstudy list --content draft` lists them.

A problem is ready when it is complete: an optimal reference in every language it lists, enough visible and hidden cases, an explanation of every approach, and, for a `dsa` problem, a slower approach, an oracle and `generator.py`. Set `status: ready` in its `meta.yaml`, then run `cstudy verify <slug> --oracle --ladder --require-ready`. When it passes, the problem is ready, and `cstudy next` can pick it.

You can keep a problem a draft as long as you like, with references in only some languages. Time limits by factor, such as `--time-limit=5x`, need an optimal reference in the language you test.

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

`cstudy new` never takes a slug that is in use, so this happens when a newer `cstudy` adds one, or when you copy a folder in by hand. To practise the catalog's problem, give yours another slug: rename its folder and change `slug` in its `meta.yaml` to match.

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
