---
title: Your workspace
summary: The folder where you practice, what each part of it holds, how cstudy finds it, and how to keep it in version control.
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
| `--ide vscode`, `--ide idea` | Writes only that IDE's project files; repeat it for both, which is the default |
| `--no-ide` | Writes no IDE project files |
| `--force` | Allows a workspace inside a checkout of the `cstudy` source |

`cstudy init` never overwrites a file, so it can turn a folder that already has files, such as a cloned repository, into a workspace.

## How cstudy finds it

Every command but a few needs a workspace. It looks, in this order:

1. `--workspace PATH`, before the command: `cstudy --workspace ~/cstudy-workspace next`.
2. The `CSTUDY_WORKSPACE` variable.
3. The nearest folder, from the current one upward, that holds `.cs/workspace.toml`.
4. The current folder.

So you can run `cstudy` anywhere inside the workspace. `cstudy init`, `cstudy doctor`, `cstudy list`, `cstudy show`, `cstudy learn` and `cstudy docs` also work outside one.

## What it holds

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
  progress.db        your attempts, reviews and runs
  .cs/               the marker, runners, language servers and caches
  .vscode/, .idea/   the IDE project files
```

| Part | What to know |
|------|--------------|
| `python/`, `typescript/`, `jvm/`, `go/`, `rust/` | Ordinary projects for each language, so your editor and its language server open them directly. Open the one you practice in, or the workspace root |
| `projects/` | A project problem is a folder of its own, started from the problem's files ([levels and projects](levels.md#project-problems)) |
| `.archive/` | When you start a review, or start again with `--fresh`, `cstudy` moves the earlier files here, under `.archive/<slug>/<attempt>-<language>/`. Nothing is deleted |
| `.statements/` | Rendered from the problem each time you start it, so there is nothing to keep |
| `progress.db` | A SQLite file with everything you did. It stays on this machine; `cstudy export` backs it up ([settings](settings.md#back-up-and-restore-your-progress)) |
| `.cs/workspace.toml` | The marker that makes the folder a workspace. Keep it |

## Keep it in version control

Your workspace is yours to version. Its `.gitignore` already leaves out what belongs to one machine: `progress.db`, the rest of `.cs/`, rendered statements, virtual environments, `node_modules` and build output. Your practice files, project folders, notes, `.archive/`, your own problems, `sets.yaml` and the IDE files stay tracked, and you commit them when you choose.

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
