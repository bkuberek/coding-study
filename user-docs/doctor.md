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
| Toolchains | Python 3.13 and uv; Node.js 24 or newer and pnpm; the JDK your shell selects, which must be 21 to 26; Go 1.25 or newer, `rustc` 1.80 or newer and `cargo`, which only warn; the debuggers of Go and Rust, which only warn. In a workspace that lists its languages, only theirs, each required ([rows by language](#rows-by-language)) |
| `cstudy` itself | Your `config.toml`, the content that ships with `cstudy`, and the `installs` row: every `cstudy` on your `PATH`, with the one that runs first |
| The workspace | Its files, its languages, `progress.db`, the Gradle wrapper, the Python project's virtual environment with `pytest` and `debugpy`, `node_modules`, and that the runner of each core language answers |
| The web UI | `web ui assets` and `web server`, which only warn, since the terminal does not need them |
| Docker | `docker` and `docker leftovers`, which only warn, since only service projects need Docker |
| Code intelligence | While it is on in the web UI's Settings, one row per language for its language server ([the editor](editor.md#turn-them-on)) |
| The AI preview | The `ai` row, while AI is on or `credentials.toml` exists: the routing and models, and the providers with a key. It only warns, since only the [AI preview](ai.md) needs it, and it asks no provider anything |

Outside a workspace it checks only the toolchains, your configuration, the content and the installs, and the `ai` row when it shows.

The `ai` row reads your configuration and `credentials.toml`, and nothing else:

```text
ok    ai on · fixed anthropic:<model id> · keys anthropic
WARN  ai on · fixed · no keys · ai.model is not set    fix: set ai.model in Settings or with cstudy config edit
```

The `java` row names the JDK and where it came from: `JAVA_HOME`, or the first `java` on your `PATH`. A JDK above 26 fails as not supported yet, and one below 21 as too old; the fix names JDK 25, the one to install ([JDK](toolchains.md#jdk)).

## Rows by language

A workspace made with `cstudy init --lang`, or narrowed with `cstudy lang remove`, lists its languages ([choose its languages](workspace.md#choose-its-languages)). `cstudy doctor` then checks those languages only: the rows of the others are left out, and `--fix` runs none of their steps. A workspace that lists none, and `cstudy doctor` outside a workspace, check all six, with Go and Rust optional.

| Rows | Shown for | When the toolchain is missing or too old |
|------|-----------|------------------------------------------|
| `python`, `uv` | `python` | `FAIL` |
| `node`, `pnpm` | `typescript`; also `python` while code intelligence is on, since pnpm installs its language server | `FAIL` |
| `java`, `gradle` | `java` or `kotlin` | `FAIL` for `java`; `WARN` for `gradle` |
| `go` | `go` | `FAIL`: you chose Go, so it is required |
| `rustc`, `cargo` | `rust` | `FAIL`: you chose Rust, so it is required |
| `dlv` | `go` | `WARN`: only `cstudy test --debug` needs it |
| `debugserver` (macOS), `lldb-server` (Linux) | `rust` | `WARN`: only `cstudy test --debug` needs it |

The workspace rows, the runners and the code intelligence rows follow the same rule, and `workspace files` covers the files of your languages and the shared ones, failing for any that is missing. A `languages` row names the languages:

```text
ok    languages python, go
ok    languages python, go (cstudy start uses python: default_lang typescript is not one of them)
ok    languages all six (none chosen; cstudy lang remove narrows them)
```

It is always `ok`: a `default_lang` outside your languages only means that `cstudy start` uses the first of them.

## Set up and repair with --fix

In a workspace, `cstudy doctor --fix` sets up what the checks need, then checks again:

```bash
cstudy doctor --fix
```

| Step | Does |
|------|------|
| Template files | Writes any file the workspace lacks, of its languages and the shared ones, such as the `go/` and `rust/` projects of a workspace made by an older `cstudy`. It never overwrites a file, and never writes the folder of a language the workspace does not list |
| Runners and progress | Refreshes the runners in `.cs/runtime/`, and migrates an older `progress.db` to the current schema |
| Python | `uv sync` in `python/`, and adds `pytest` when it is missing |
| TypeScript | `pnpm install` in `typescript/` |
| Java and Kotlin | A first Gradle build in `jvm/`, which downloads Gradle and the libraries once, so later builds need no network. It is skipped, with a `FAIL` that names the JDK to select, when the selected JDK is missing or older than 21 |
| Docker | Starts a stopped engine, and removes what a service project left behind, by its labels only |
| Language servers | While code intelligence is on, installs them into `.cs/lsp/` ([the editor](editor.md#turn-them-on)). With it off it installs none and says so |

In a workspace that lists its languages, `--fix` runs only their steps: `uv sync` with Python, `pnpm install` with TypeScript, the Gradle build with Java or Kotlin. Go and Rust need no setup step: everything their runners use ships with `cstudy`. `--fix` needs a workspace, and exits 3 outside one. It needs the network the first time; after that, practice needs no network.

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

## Row reference

Every row is `ok` when its check passes. This table says when each one is not, and what fixes it. `cstudy doctor` exits 0 when no row is `FAIL`, and 4 when one is. `--json` with `--fix` is refused with exit 3, and so is `--fix` outside a workspace.

| Row | Status | When | Fix |
|-----|--------|------|-----|
| `python` | `FAIL` | uv is not found, uv finds no Python 3.13, or the interpreter prints no version | Install uv ([Python and uv](toolchains.md#python-and-uv)); for a missing Python, `uv python install 3.13` |
| `uv` | `FAIL` | `uv` is not on your `PATH`, or prints no version | Install uv ([Python and uv](toolchains.md#python-and-uv)) |
| `node` | `FAIL` | Node.js is missing, or older than 24 | Install Node 24 or newer ([Node.js and pnpm](toolchains.md#nodejs-and-pnpm)) |
| `pnpm` | `FAIL` | pnpm is missing | Install pnpm ([Node.js and pnpm](toolchains.md#nodejs-and-pnpm)) |
| `java` | `FAIL` | No JDK is found, `JAVA_HOME` holds no JDK, or the selected JDK is older than 21 or newer than 26 | Select a JDK 21 to 26 with `JAVA_HOME`, or install JDK 25 ([JDK](toolchains.md#jdk)) |
| `gradle` | `WARN` | No Gradle of your own. Only regenerating the Gradle wrapper needs one: the workspace's wrapper downloads its own | `brew install gradle`, or nothing |
| `go` | `WARN` or `FAIL` | Go is missing, or older than 1.25. `FAIL` when the workspace lists Go; otherwise `WARN`, since only `--lang go` needs it | Install Go 1.25 or newer ([Go](toolchains.md#go)) |
| `rustc` | `WARN` or `FAIL` | Rust is missing, or older than 1.80. `FAIL` when the workspace lists Rust; otherwise `WARN`, since only `--lang rust` needs it | Install Rust 1.80 or newer with rustup ([Rust](toolchains.md#rust)) |
| `cargo` | `WARN` or `FAIL` | cargo is missing. `FAIL` when the workspace lists Rust | Install Rust with rustup ([Rust](toolchains.md#rust)) |
| `dlv` | `WARN` | Delve is missing or prints no version, or your Go is older than the Go this Delve debugs. Only `cstudy test --debug` with Go needs it | `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`, or install the Go the row names ([Go](toolchains.md#go)) |
| `debugserver` (macOS), `lldb-server` (Linux) | `WARN` | Rust's debug server is not found. Only `cstudy test --debug` with Rust needs it | On macOS `xcode-select --install`; on Linux your distribution's `lldb` package ([Rust](toolchains.md#rust)) |
| `docker` | `WARN` | Docker is installed and not running, Docker refuses you, or Docker is missing or has no Compose v2. Only service projects need it | Not running: `cstudy doctor --fix` starts it. Refused: the step the row names, such as joining the `docker` group. Missing: install it ([which Docker](toolchains.md#which-docker)) |
| `docker leftovers` | `WARN` | A service project's run ended without cleaning up after itself, or Docker could not list what it left | `cstudy doctor --fix` removes what is left, by the labels `cstudy` puts on it |
| `config` | `FAIL` | `config.toml` does not load. The row names each wrong key | Correct those keys: `cstudy config edit` opens the file ([your configuration](settings.md#your-configuration)) |
| `ai` | `WARN` | Only while AI is on or `credentials.toml` exists: AI is on and a model the routing needs is not set, or its provider has no key; `credentials.toml` does not load; it lies in a Git working tree; or it would lie inside the workspace | The `fix:` names the key to set, `cstudy ai key <provider>`, the file to correct, or the `.gitignore` to add it to ([your keys](ai.md#your-keys)) |
| `content` | `FAIL` | The problems and runners that ship with `cstudy` are not found | Reinstall `cstudy`. If you set `CSTUDY_CONTENT` or pass `--content`, it must name a folder with `problems/` and `schemas/` |
| `installs` | `WARN` | More than one `cstudy` is on your `PATH`, and only the first runs | Keep one: the fix names the command that removes each other copy ([several installs](#several-installs)) |
| `workspace` | `WARN` or `FAIL` | `WARN`: no workspace here. `FAIL`: its marker, `.cs/workspace.toml`, does not read, or a newer `cstudy` wrote it | `WARN`: `cstudy init`, or run inside your workspace. `FAIL`: repair the file the row names, or upgrade `cstudy` ([older workspaces](upgrading.md#older-workspaces)) |
| `languages` | always `ok` | It names the workspace's languages, or says it has all six. A marker whose `languages` does not read fails the `workspace` row instead | `cstudy lang add` and `cstudy lang remove` change them ([choose its languages](workspace.md#choose-its-languages)) |
| `workspace files` | `FAIL` or `WARN` | `FAIL`: a template file of the workspace's languages, or a shared one, is missing. `WARN`: a folder of your `problems/` loads as no problem, because its name is not a slug or its `meta.yaml` has an `id:` line | `FAIL`: `cstudy doctor --fix`. `WARN`: the `mv` to run and the line to delete, which the row names |
| `go and rust files` | `WARN` | `go.work`, or files of `go/` and `rust/`, are missing, as in a workspace made before Go and Rust. Only in a workspace that has not chosen its languages: a chosen Go or Rust is part of `workspace files` | `cstudy doctor --fix` |
| `projects` | `WARN` | There is no `projects/` folder, as in a workspace made before project problems | `cstudy doctor --fix` |
| `runner runtime` | `FAIL` | `.cs/runtime/` is missing, or older than the content | `cstudy doctor --fix` |
| `progress database` | `WARN` or `FAIL` | `WARN`: an older schema, which migrates on next use. `FAIL`: a newer schema than this `cstudy` reads, or a file that is not a progress database | `WARN`: `cstudy doctor --fix` migrates it now. `FAIL`: upgrade `cstudy` ([older workspaces](upgrading.md#older-workspaces)) |
| `jvm/gradlew` | `WARN` or `FAIL` | `WARN`: there is no `jvm/` project yet. `FAIL`: `jvm/` has no Gradle wrapper | `cstudy doctor --fix` writes the wrapper back |
| `python/.venv` | `WARN` or `FAIL` | `WARN`: there is no `python/` project yet. `FAIL`: its virtual environment is missing | `cstudy doctor --fix` |
| `typescript/node_modules` | `WARN` or `FAIL` | `WARN`: there is no `typescript/` project yet. `FAIL`: its `node_modules` is missing | `cstudy doctor --fix` |
| `python debugpy` | `WARN` | debugpy is not installed in `python/.venv`. Only `cstudy test --debug` needs it | `uv add --dev debugpy --directory python` |
| `python pytest` | `WARN` | pytest is not installed in `python/.venv`. Only Python project problems need it | `cstudy doctor --fix` |
| `project links` | `WARN` | The `.venv` link of a Python project folder is missing or dangling | `cstudy doctor --fix` |
| `go projects` | `WARN` | A Go project folder has no `go.work`, has a `replace` line that does not resolve, or shares its module path with another folder | No `go.work`: `cstudy doctor --fix`. A `replace`: `cstudy start <slug> --restore go.mod`. A shared module: give each folder a module of its own in its `go.mod` |
| `rust project config` | `WARN` | The `.cargo/config.toml` of a Rust project folder is missing or does not resolve | `cstudy doctor --fix` |
| `rust linked projects` | `WARN` | A Rust project folder is missing from `rust-analyzer.linkedProjects` in `.vscode/settings.json` | `cstudy ide` |
| `python/.venv location` | `WARN` | The workspace moved, so the console scripts of the virtual environment name the old path and no longer run. `cstudy` itself still works | `rm -rf python/.venv && cstudy doctor --fix` |
| `runner python`, `runner typescript`, `runner java`, `runner kotlin` | `FAIL` | The language's runner does not build, or does not answer | `cstudy doctor --fix`. For Java and Kotlin, check the `java` row first |
| `java project libraries`, `kotlin project libraries` | `WARN` | The libraries that Java and Kotlin project folders build with are not cached yet. Only project problems need them | `cstudy doctor --fix`, once with the network |
| `web ui assets` | `WARN` | A file of the web UI is missing or damaged. Only `cstudy serve` needs them | The reinstall command of the install that runs, such as `brew reinstall cstudy` |
| `web server` | `WARN` | A library of the web server does not import. Only `cstudy serve` needs them | The same reinstall command |
| `code intelligence <language>`, `code intelligence <language> service projects` | `WARN` | Only while code intelligence is on: the language server is not installed, is another version, or cannot run on the selected JDK; for Kotlin, its license is not accepted, or its build stops working soon | `cstudy doctor --fix`. For Kotlin's license, `cstudy doctor --fix --accept-license kotlin-lsp`. For Rust, `rustup component add rust-analyzer`. For a JDK, the one the row names ([the editor](editor.md#turn-them-on)) |
