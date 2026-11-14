---
title: Check your setup with cstudy doctor
summary: What cstudy doctor checks, what ok, WARN and FAIL mean, and how --fix sets up and repairs a workspace.
section: Start here
order: 30
---

# Check your setup with cstudy doctor

`cstudy doctor` checks that everything `cstudy` needs is in place, and prints one row per check. A row that needs you ends with a `fix:`, the command or the step that repairs it. Run it after you install `cstudy` or a toolchain, after an upgrade, and whenever something does not work.

```bash
cstudy doctor
```

```text
ok    python 3.13.2
ok    uv 0.10.11
ok    node v24.18.0 (type stripping)
ok    pnpm 9.15.9
ok    java 25.0.5 (JAVA_HOME)
ok    workspace /home/me/ws (created with cstudy 0.1.0)
FAIL  python/.venv missing    fix: cstudy doctor --fix
ok    runner python answers hello: python 3.13.2, protocol 1
```

## What the rows mean

| Status | Means |
|--------|-------|
| `ok` | The check passed |
| `WARN` | Something is missing or old, but practice works without it: an optional toolchain such as Go or Rust, a debugger only `cstudy test --debug` needs, a project not set up yet, Docker for service projects, or several copies of `cstudy` on your `PATH` |
| `FAIL` | Something blocks practice. Its `fix:` says what to do |

It exits 0 when no row is `FAIL`, and 4 otherwise, so a script can stop on it.

## What it checks

| Group | Rows |
|-------|------|
| Toolchains | Python 3.13 and uv; Node.js 24 or newer and pnpm; the JDK your shell selects, which must be 21 to 26; Go 1.25 or newer, `rustc` 1.80 or newer and `cargo`, which only warn; the debuggers of Go and Rust, which only warn |
| `cstudy` itself | Your `config.toml`, the content that ships with `cstudy`, and the `installs` row: every `cstudy` on your `PATH`, with the one that runs first |
| The workspace | Its files, `progress.db`, the Gradle wrapper, the Python project's virtual environment with `pytest` and `debugpy`, `node_modules`, and that the runner of each core language answers |
| The web UI | `web ui assets` and `web server`, which only warn, since the terminal does not need them |
| Docker | `docker` and `docker leftovers`, which only warn, since only service projects need Docker |
| Code intelligence | While it is on in the web UI's Settings, one row per language for its language server ([the editor](editor.md#turn-them-on)) |

Outside a workspace it checks only the toolchains, your configuration, the content and the installs.

The `java` row names the JDK and where it came from: `JAVA_HOME`, or the first `java` on your `PATH`. A JDK above 26 fails as not supported yet, and one below 21 as too old; the fix names JDK 25, the one to install ([JDK](toolchains.md#jdk)).

## Set up and repair with --fix

In a workspace, `cstudy doctor --fix` sets up what the checks need, then checks again:

```bash
cstudy doctor --fix
```

| Step | Does |
|------|------|
| Template files | Writes any file the workspace lacks, such as the `go/` and `rust/` projects of a workspace made by an older `cstudy`. It never overwrites a file |
| Runners and progress | Refreshes the runners in `.cs/runtime/`, and migrates an older `progress.db` to the current schema |
| Python | `uv sync` in `python/`, and adds `pytest` when it is missing |
| TypeScript | `pnpm install` in `typescript/` |
| Java and Kotlin | A first Gradle build in `jvm/`, which downloads Gradle and the libraries once, so later builds run offline. It is skipped, with a `FAIL` that names the JDK to select, when the selected JDK is missing or older than 21 |
| Docker | Starts a stopped engine, and removes what a service project left behind, by its labels only |
| Language servers | While code intelligence is on, installs them into `.cs/lsp/` ([the editor](editor.md#turn-them-on)). With it off it installs none and says so |

Go and Rust need no setup step: everything their runners use ships with `cstudy`. `--fix` needs a workspace, and exits 3 outside one. It needs the network the first time; after that, practice works offline.

Kotlin's language server comes under a license you accept first. `--fix` asks at a terminal, or you accept it up front:

```bash
cstudy doctor --fix --accept-license kotlin-lsp
```

The Health view of the web UI (`Alt+6`) shows the same rows, with a **Fix** button that runs `cstudy doctor --fix`. It never accepts a license for you.

## For scripts

`--json` prints the same checks as one JSON document, and exits as the rows would:

```bash
cstudy doctor --json
```

```json
{"workspace": "/home/me/ws", "passed": false, "checks": [
  {"name": "python", "status": "ok", "detail": "3.13.2", "fix": null},
  {"name": "python/.venv", "status": "fail", "detail": "missing", "fix": "cstudy doctor --fix"}
]}
```

`--json` and `--fix` do not go together.

## Several installs

When more than one `cstudy` is on your `PATH`, the `installs` row warns. Only the first one runs, so repairing or upgrading another changes nothing. The row's fix keeps the newest and names the command that removes each other copy, such as `brew uninstall cstudy`, `uv tool uninstall coding-study` or `pipx uninstall coding-study`.

## What the checks may read

The setup commands of `--fix` and the version checks run with part of your shell's environment, as your code does: your proxy and certificate settings reach them, so an install behind a company network works, and a token you exported does not ([your environment](toolchains.md#your-environment)).
