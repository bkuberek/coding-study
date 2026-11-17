---
title: Your workspace
summary: The folder where you practice, what each part of it holds, the languages it practices, how cstudy finds it, and how to keep it in version control.
section: Start here
order: 40
---

# Your workspace

A workspace is a folder of your own where you practice: your solutions, your notes, your own problems and sets, and your progress. It is separate from `cstudy`, which you install once with its problems; you can have several workspaces, and keep each in a git repository of your own.

## Create one

```bash
cstudy init ~/cstudy-workspace --git
cd ~/cstudy-workspace
cstudy doctor --fix
```

`cstudy init` copies the workspace's files, writes the IDE project files for VS Code and IntelliJ IDEA, and with `--git` runs `git init`; `cstudy` never commits for you. It installs nothing: `cstudy doctor --fix` installs each project's dependencies.

| Flag | Does |
|------|------|
| `--git` | Runs `git init` in the new workspace |
| `--lang <language>` | A language you practice there; repeat it for several. The workspace gets only those languages' folders ([choose its languages](#choose-its-languages)). Without it, it has all six |
| `--ide vscode`, `--ide idea` | Writes only that IDE's project files; repeat it for both, which is the default |
| `--no-ide` | Writes no IDE project files |
| `--force` | Allows a workspace inside a checkout of the `cstudy` source |

`cstudy init` never overwrites a file, so it can turn a folder that already has files, such as a cloned repository, into a workspace.

To practice only Python and Go, for instance:

```bash
cstudy init ~/cstudy-workspace --lang python --lang go
```

## How cstudy finds it

Every command but a few needs a workspace. It looks, in this order:

1. `--workspace PATH`, before the command: `cstudy --workspace ~/cstudy-workspace next`.
2. The `CSTUDY_WORKSPACE` variable.
3. The nearest folder, from the current one upward, that holds `.cs/workspace.toml`.
4. The current folder.

So you can run `cstudy` anywhere inside the workspace. `cstudy init`, `cstudy doctor`, `cstudy list`, `cstudy show`, `cstudy learn` and `cstudy docs` also work outside one.

## What it holds

A workspace with all six languages holds:

```text
cstudy-workspace/
  python/            the Python project: practice/<slug>.py
  typescript/        the TypeScript project: practice/<slug>.ts
  jvm/               the Java and Kotlin projects, with the Gradle wrapper
  go/                the Go module: practice/<slug>/
  rust/              the Rust package: practice/<slug>.rs
  go.work            lets Go tools find go/ from the workspace root
  projects/          one folder per project problem you started
  notes/             your answers to system design and code review
  problems/          problems of your own
  sets.yaml          your problem sets
  .archive/          the files of earlier attempts
  .statements/       the statements cstudy renders
  progress.db        your attempts, reviews, runs and AI reviews
  .cs/               the marker, runners, language servers and caches
  .vscode/, .idea/   the IDE project files
```

| Part | What to know |
|------|--------------|
| `python/`, `typescript/`, `jvm/`, `go/`, `rust/` | Ordinary projects for each of the workspace's languages, so your editor and its language server open them directly. Open the one you practice in, or the workspace root |
| `projects/` | A project problem is a folder of its own, started from the problem's files ([levels and projects](levels.md#project-problems)) |
| `.archive/` | When you start a review, or start again with `--fresh`, `cstudy` moves the earlier files here, under `.archive/<slug>/<attempt>-<language>/`. Nothing is deleted |
| `.statements/` | Rendered from the problem each time you start it, so there is nothing to keep |
| `progress.db` | A SQLite file with everything you did, your AI reviews, AI requests and AI consents among it. It stays on this machine; `cstudy export` backs it up, with the AI reviews and without the AI requests and consents, which belong to this machine ([settings](settings.md#back-up-and-restore-your-progress)) |
| `.cs/workspace.toml` | The marker that makes the folder a workspace, with its languages. Keep it |

## Choose its languages

A workspace's languages decide which practice folders it has, which toolchains `cstudy doctor` checks, which IDE files it gets and which languages a new attempt starts in. They are also the languages of your [learner profile](settings.md#your-learner-profile), so the lists and picks of `cstudy` show what you can practice here.

| Language | Its folders |
|----------|-------------|
| `python` | `python/` |
| `typescript` | `typescript/` |
| `java`, `kotlin` | `jvm/`, one Gradle build that holds both, so either language writes it |
| `go` | `go/` and `go.work` |
| `rust` | `rust/` |

Every workspace also has `notes/`, `problems/`, `projects/`, `README.md`, `.gitignore` and the marker.

A workspace made without `--lang`, as every workspace made before languages could be chosen, has all six: every folder, with Python, TypeScript, Java and Kotlin required by `cstudy doctor` and Go and Rust optional. Once a workspace lists its languages, each of them is required, Go and Rust included, and the others are left out of `cstudy doctor`, `cstudy doctor --fix` and the IDE files.

```bash
cstudy lang list            # the languages and their folders
cstudy lang add go          # writes go/ and go.work
cstudy doctor --fix         # then installs the new language's toolchain files
cstudy lang remove rust     # rust/ stays on disk
```

`cstudy lang add` writes the folder files the language lacks, never overwriting one, and refreshes the IDE files `cstudy` wrote. The **profile** section of Settings adds and removes languages too ([the Profile section](settings.md#the-profile-section)).

A new attempt starts only in one of the workspace's languages. Another exits 3 and writes nothing, with the command that adds it:

```text
error: rust is not one of this workspace's languages (python, go): cstudy lang add rust
```

An attempt already in progress still resumes, and a [service project](service-projects.md) starts whatever the languages, since it runs in Docker. Without `--lang`, `cstudy start` uses `default_lang` when it is one of the workspace's languages, else the first of them.

### Remove a language

`cstudy lang remove` takes a language out of the workspace and keeps its folder: the folder and your practice files stay on disk, and are no longer checked, written or offered. Progress, `.archive/`, `projects/` and `notes/` always stay. Removing `java` while `kotlin` stays keeps `jvm/` in use. A workspace needs at least one language, so removing the last one is refused. An attempt in progress in a removed language can still be resumed and finished while its files are there.

### Delete its folder

`--delete-folder` also deletes the language's folders, whole, with their toolchain files. It first shows what goes and what stays, then asks:

```text
$ cstudy lang remove rust --delete-folder
delete     rust/ (12 practice files)
stays      progress, .archive/, projects/ and notes/
Delete rust/? Its 12 practice files can't be recovered. [y/N]: y
removed    rust
deleted    rust/ (12 practice files)
ide        vscode · 1 updated
```

A no, Enter alone or `Ctrl+D` leaves everything as it was. `--yes` does not ask, for a script; without a terminal to ask you and without `--yes`, it refuses with exit 3 and changes nothing. It also refuses, with nothing changed, while an attempt in a removed language is in progress, until you finish it with `cstudy done` or end it with `cstudy abort`, and while a run or a job is active. `jvm/` goes only once neither Java nor Kotlin remains. A deleted folder can't be recovered, so commit or copy what you want to keep first. On a language the workspace no longer lists, `--delete-folder` deletes the folder it left behind.

## Keep it in version control

Your workspace is yours to version. Its `.gitignore` already leaves out what belongs to one machine: `progress.db`, the rest of `.cs/`, rendered statements, virtual environments, `node_modules` and build output. Your practice files, project folders, notes, `.archive/`, your own problems, `sets.yaml`, the IDE files and the marker, with the workspace's languages, stay tracked, and you commit them when you choose.

Your AI keys are never in a workspace: `credentials.toml` sits beside your `config.toml`, and `cstudy` refuses to read or write it inside a workspace ([your keys](ai.md#your-keys)). Never commit a key to the workspace's repository, or to any other.

To keep your progress too, commit a backup:

```bash
cstudy export          # writes progress-export.json, which you can commit
```

On another machine, clone your workspace, then:

```bash
cstudy doctor --fix
cstudy import          # restores progress-export.json into an empty progress.db
```

## Your IDE

`cstudy init` writes project files for VS Code and IntelliJ IDEA: tasks and run configurations for every `cstudy` action, and debug configurations that attach to a run of `cstudy test --debug`. `cstudy ide` writes them again, and keeps the files you edited. [Your IDE and the debugger](ide-and-debugging.md) covers what each file holds and how to debug a run.

## Your own problems

`cstudy new` scaffolds a problem in the workspace's `problems/`, and it joins the catalog for every command. [Write your own problems](own-problems.md) covers the templates, the files, the checks of `cstudy verify` and the way from draft to ready.
