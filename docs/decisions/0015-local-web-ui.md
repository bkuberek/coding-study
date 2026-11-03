# ADR 0015: A local web UI, served by `cstudy serve`, with full practice parity

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-31 |
| Spec | [web-ui](../specs/web-ui.md), [cli](../specs/cli.md#cstudy-serve) (`cstudy serve`, the [event stream](../specs/cli.md#event-stream) for every kind, `cstudy history`, the new `--json` documents), [installation-and-workspaces](../specs/installation-and-workspaces.md#web-ui-assets), [architecture](../architecture.md#web-adapter) |
| Amends | [PRD](../prd.md) (the web UI leaves the non-goals: FR-16, NFR-10 to NFR-12), [ADR 0014](0014-project-problems.md) (its web interface revisit trigger) |
| Amended by | [ADR 0018](0018-editor-code-intelligence.md): the editor gains a language service from local language servers, behind a setting; one WebSocket route, for language-server sessions only; the revisit trigger for a language-server bridge is closed |
| Builds on | [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0010](0010-ide-integration.md), [ADR 0013](0013-homebrew-distribution.md), [ADR 0014](0014-project-problems.md) |

## Context

`cstudy` is used from a terminal beside an editor. The owner wants a browser page on the same machine where the whole practice loop happens: browse and pick a problem, read the statement, edit the code, run the tests and submit with results arriving live, take hints, reveal solutions, finish the attempt, run mock interviews, and see progress and workspace health. The project-problem work built the boundary such a page needs: an event stream (`--events`), diagnostics with file and line, a starter manifest with file states and restore, and a lock per project ([ADR 0014](0014-project-problems.md)). That boundary covered project problems only.

A design proposal with spikes (commit `4819ff9`, removed by this ADR's commit) measured the options. The facts it established, on a heavily loaded machine:

| Spike | Result |
|-------|--------|
| Editor bundle | CodeMirror 6 with six languages, JSON and TOML: 737.5 KB raw, 262.9 KB gzip in 12 files, 468.8 KB raw for a Python session. Monaco: 4,548 KB raw, 1,141.5 KB gzip, plus a worker |
| Vim keybindings | `codemirror-vim` 6.4.0: 120.2 KB raw, 38.3 KB gzip, MIT |
| Server libraries | starlette 1.10.0, uvicorn 0.54.0 and h11 0.16.0: three pure-Python wheels, 200.7 KB in all |
| Cancel | SIGINT to `cstudy test --events` during a slow test: `run_end` `interrupted` 2 ms later, exit 130 after 58 to 63 ms, no runner left, no `test_runs` row |
| Run slot | A run requested right after a cancel must wait for the child to exit, not for `run_end` |
| CSP | CodeMirror needs `EditorView.cspNonce` under `style-src 'self' 'nonce-…'`; without it Chromium leaves the editor unstyled |
| Browser | A headless Chromium smoke test of a spike server passed 13 checks: cookie login, Host and Origin refusals, CSRF header, CSP, streamed run, cancel, a load error marked on its line |

## Decision

- **A second driving adapter.** `cstudy serve [--port N] [--open]` serves a page on `127.0.0.1` from a new package `coding_study.entrypoints.web`: a Starlette app on uvicorn, imported only when `cstudy serve` runs. It is local to the user's machine and binds no other address.
- **Full practice parity (O1 = c, and the owner's "web UI with full support").** Version 1 covers everything a user does while practising, for every kind (function, design, progressive, concurrent, debugging, project and the non-autograded items) and every language: browsing with filters and the `cstudy next` pick, `start`, live `test`, `submit`, `hint`, `solution`, `done`, `status` with the project file tree and restore, mock interviews, statistics, the review schedule and history per problem, a `doctor` view with `doctor --fix`, `verify` of your own problems and `bench` as streamed jobs, and progress export and import. [web-ui](../specs/web-ui.md#command-parity) maps every command to its endpoint and use case.
- **The CLI first, the page second.** The page never gets behaviour the CLI lacks. Each endpoint calls the application use case the command calls and returns the command's `--json` document unchanged where one exists. Where the page needs values no command prints, the CLI gains them first: `--json` for `cstudy list`, `cstudy next` and `cstudy doctor`, `cstudy list --kind`, `cstudy status` for every kind, a new `cstudy history`, and `--events` for every kind ([cli](../specs/cli.md#event-stream)).
- **Runs and jobs are child processes.** A page run starts `python -m coding_study test|submit … --events` and relays each line as a server-sent event, unchanged; cancel sends SIGINT. `doctor --fix`, `verify` and `bench` run the same way as text jobs. Reads and small writes call use cases in-process, serialized through one worker thread.
- **The event stream covers every kind.** Single-file runs report each case, oracle input and stress run as it ends; the build, time-limit verdicts, level unlocks and the `--perf` check are events of their own. Version 1 of the stream stays: every line a project stream produced before is unchanged, and the additions are new event types, new fields and a nullable `levels` on streams that did not exist before ([cli](../specs/cli.md#version)).
- **Editor: CodeMirror 6 (O2 = a)**, each language loaded on first use, built with esbuild from `tools/web-ui/` and committed under the package with a digest manifest, as the IntelliJ launcher jar is ([ADR 0010](0010-ide-integration.md)). No network request at runtime.
- **Vim keybindings: an opt-in preference, loaded lazily (O4 = a).** Preferences live in the workspace's `.cs/serve/preferences.json`.
- **Timer and mock interviews from the page (O3 = b).** The page starts a mock as `cstudy mock` does, with the same picks, shared timer, and hint and solution lock.
- **Reference solutions in the page (O7 = b),** behind the confirmation `cstudy solution` asks, recorded as revealed. Progress import needs a confirmation too, and so does `doctor --fix`.
- **The browser opens only with `--open` (O5 = a).**
- **Security.** A session token exchanged for an `HttpOnly` `SameSite=Strict` cookie, Host and Origin allow-lists, a CSRF header on every unsafe request, a strict Content Security Policy with a per-page nonce, no CORS, and a file API confined to the files of the attempts in progress that never follows a link ([web-ui](../specs/web-ui.md#security)).
- **Testing (O6 = a, O8 = b).** API and streaming tests run without a browser; one Playwright smoke test sits in an optional development group and runs with the slow tests when installed. A CI workflow for lint, types, contracts and fast tests is added by a separate Linux task (F9).

### Owner answers

| # | Question | Answer |
|---|----------|--------|
| O1 | Which problem kinds version 1 covers | (c) every kind, live, which needs `cstudy test --events` for every kind first; widened the same day to full practice parity |
| O2 | Editor | (a) CodeMirror 6 |
| O3 | Timer and mock interviews | (b) the timer, and mock interviews started from the page |
| O4 | Vim keybindings | (a) an opt-in setting, loaded lazily |
| O5 | Opening the browser | (a) only with `--open` |
| O6 | Browser smoke test | (a) Playwright in an optional development group |
| O7 | Reference solutions | (b) viewable in the page behind the CLI's confirmation, recorded as revealed |
| O8 | A test workflow | (b) added, owned by task F9 |

### Commands that stay in the terminal

| Command | Why |
|---------|-----|
| `cstudy init` | Creates the workspace that `cstudy serve` needs before it can start |
| `cstudy ide` | Writes files for VS Code and IntelliJ; it has no use inside the page |
| `cstudy serve` | Starts the page |
| `cstudy new` | Scaffolds a problem across several content files and templates, written in an editor over the content tree |
| `cstudy verify` on catalog problems | A maintainer's gate, run in a content checkout; the page verifies only your own problems |
| `cstudy test --debug` | Needs an IDE's debugger attached to the runner ([ADR 0010](0010-ide-integration.md)) |
| `cstudy test --watch` | Replaced by the page's run-on-save preference, which re-runs the tests the same way |
| `cstudy export --out`, `cstudy import PATH` | The page downloads and uploads the same document instead of naming a path |

## Consequences

- New runtime dependencies: starlette, uvicorn (without its `standard` extra) and h11, three pure-Python wheels that reach the Homebrew formula through `requirements.txt` with no template change ([ADR 0013](0013-homebrew-distribution.md)). The wheel grows by the vendored assets, about 0.3 MB compressed.
- `entrypoints/commands/serve.py` imports the web stack inside the command only, so NFR-2 is unchanged; a test asserts that importing `coding_study.entrypoints.cli` loads neither Starlette nor uvicorn. Import contracts forbid both libraries to the domain, the application and the adapters.
- New CLI surface before the page can use it: `cstudy test --events` for every kind (task U14), and `cstudy list --json` and `--kind`, `cstudy next --json`, `cstudy doctor --json`, `cstudy status` for every kind and `cstudy history`. A run started from the page and one started in the terminal behave the same, because they are the same command.
- New application use cases for the files of an attempt (`application/attempt_files.py`: tree, read, save, create, move, delete) and for a problem's history; new `Workspace` methods that never follow a link.
- `.cs/serve/` in the workspace holds the preferences and the transient redirect file of `--open`.
- Contributors who change the front end need Node 24 and npm to rebuild `tools/web-ui/`; installing `cstudy` needs neither, because the built bundle is committed.
- A page run costs what a terminal run costs, the CLI's own start included, so it meets NFR-1 when `cstudy test` does. The spikes ran on a loaded machine; task U11 measures page runs on a quiet one.
- Build errors in Java, Kotlin, Go and Rust carry no file or line until task U13 adds their parsers; they show in the results panel without editor markers.
- The PRD's non-goals no longer list a web UI or a browser editor, and ADR 0014's revisit trigger for a web interface is closed by this ADR.

## Revisit

| Trigger | What to reconsider |
|---------|--------------------|
| A page run's p50 misses its NFR-11 target on a quiet machine | Runs in-process, with a cancellation port through the runner and every build step |
| Streams hit the browser's six HTTP/1.1 connections per host in normal use | One multiplexed stream per tab, or HTTP/2 |
| A need the editor cannot meet, such as code completion from a language server | A language-server bridge, or Monaco |
| The page's own code outgrows plain TypeScript views | Preact, within the asset budget of NFR-12 |
| A practice command is added to the CLI | Its endpoint and page area, in the same change |

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Version 1 for project problems only (O1 a) | The owner wants the page for all practice, and the single-file kinds are most of the catalog |
| Single-file kinds through `cstudy test --json`, without live results (O1 b) | A concurrent or JVM run takes seconds; a page that shows nothing until the end is worse than the terminal |
| Runs in-process, in a worker thread | Saves one CLI start per run, but needs a cancellation port through the runner and every build step, shares state across threads, and lets a failing run take the server down |
| Page-only behaviour, such as a hint view or a status the CLI cannot show | Two front ends would drift; every value the page shows comes from a command first |
| Monaco (O2 b) | Six times the raw size, a worker, CSS and a font, for highlighting the same six languages |
| No timer, or a timer without mocks (O3 a, c) | Mocks pick single-file problems too, which version 1 now covers |
| Opening the browser by default (O5 b) | Surprising over SSH and in scripts |
| WebSocket | Needs a WebSocket implementation for uvicorn and our own reconnect and replay; every client action is an ordinary request anyway |
| Standard-library `http.server` | Routing, parsing, streaming and the security checks would all be custom code, with no test client |
| aiohttp, FastAPI | Compiled extensions for the Homebrew formula, or validation the API does in a few lines |
| Build the bundle at install time, or only in the release workflow | Every install from git would need Node; `uv tool install git+…` would lack the bundle |
| The token on every request, no cookie | `EventSource` cannot send headers, and the token would sit in every request line |
| Preferences in the browser's local storage | The origin includes the port, which changes on every start, so preferences would be lost |
