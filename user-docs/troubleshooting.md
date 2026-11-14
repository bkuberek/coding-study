---
title: Troubleshooting
summary: What to do when a command fails, a toolchain is missing, the web UI loses its server, or a language server stops.
section: Settings and help
order: 130
---

# Troubleshooting

Start with `cstudy doctor`. It checks every toolchain, your configuration, the content, the installs on your `PATH` and the workspace, and prints a `fix:` for each row that needs one ([check your setup](doctor.md)). Most problems end there.

```bash
cstudy doctor        # what is wrong, and the fix for each row
cstudy doctor --fix  # in a workspace: set up the projects and repair what it can
```

## Exit codes

Every command ends with a code that says how it went, which scripts can read:

| Code | Means |
|-----:|-------|
| 0 | It worked; every case passed |
| 1 | Some cases or checks failed, a time limit included |
| 2 | Your code did not build or load: a compile error, an import error, a missing name |
| 3 | The command was wrong: a flag, a slug that does not exist, no attempt in progress |
| 4 | Something on your machine is missing: a toolchain, a JDK in range, a runner that did not start |
| 5 | A content file is wrong: a problem, a guide or a page that fails its checks |
| 70 | A bug in `cstudy`. Please report it |
| 130 | You stopped it with `Ctrl+C` |

## Commands

| You see | Do |
|---------|----|
| `no coding-study workspace at …: run cstudy init` | Run the command inside your workspace, pass `--workspace PATH`, or set `CSTUDY_WORKSPACE`. Create one with `cstudy init` ([your workspace](workspace.md)) |
| `unknown problem "…"` | `cstudy list --search <word>` finds the slug |
| `no attempt in progress; start one with cstudy start <slug>` | Start one, or name the problem: `cstudy test two-sum` |
| A `FAIL` row in `cstudy doctor` | Run the `fix:` it prints. For a toolchain, follow [install the language toolchains](toolchains.md) |
| `cstudy doctor` warns on `installs` | Several copies of `cstudy` are on your `PATH`, and only the first runs. Keep one: the row's `fix:` names the command that removes each other copy. `which -a cstudy` lists them |
| `java 27 (not supported yet …)` or a JDK that is too old | `cstudy` runs Java and Kotlin on JDK 21 to 26. Select one with `JAVA_HOME`, or install JDK 25 ([JDK](toolchains.md#jdk)) |
| `go was not found on PATH`, `cargo was not found on PATH` | Go and Rust are optional; install them only for `--lang go` or `--lang rust` ([Go](toolchains.md#go), [Rust](toolchains.md#rust)) |
| The first Java or Kotlin run is slow | Gradle starts its daemon and compiles once; later runs are quicker. `cstudy doctor --fix` warms it up ahead of time |
| `progress.db` is newer than this `cstudy` | A newer `cstudy` wrote it. Upgrade `cstudy` |
| `cstudy hint is locked during the mock interview` | Hints and solutions unlock when the mock's timer ends or every problem is done ([mock interviews](planning.md#mock-interviews)) |
| A service project says Docker is missing or not running | Install or start Docker; `cstudy` starts a stopped engine itself when it can, and says what to run when it cannot ([Docker](toolchains.md#docker)) |
| Output with colours you do not want | Pass `--no-color`, or set `NO_COLOR`. Output to a pipe or a file has no colours |

## The web UI

| You see | Do |
|---------|----|
| "This browser has no session with this server" | Open the URL the server printed. The token in it is new every time the server starts |
| `port … is already in use` | Another program holds the port: pick another with `--port`, or leave it out to get a free one |
| `reconnecting…` in the top bar | The page lost the server for a moment and tries again |
| `disconnected` in the top bar | The server stopped or restarted: start it again and open the new URL |
| `cstudy serve` exits 4, or `cstudy doctor` warns on `web ui assets` or `web server` | The page's files or the web server libraries are missing or damaged: reinstall `cstudy` with the command `cstudy doctor` prints, which names the install that runs; if it also warns on `installs`, keep one install first |
| A language fails in the Health view | Install its toolchain ([toolchains](toolchains.md)), then use **Fix**, on its row or at the top of the view, which runs `cstudy doctor --fix` |
| The dev stack panel says `cstudy dev` is already running in a process | A terminal holds the project's dev stack: stop it there with `Ctrl+C`, or use that one |
| `Tab` skips buttons and links in Safari | Use `Option+Tab`, or turn on "Press Tab to highlight each item on a webpage" in Safari's Advanced settings |

## Code intelligence

| You see | Do |
|---------|----|
| `not installed: run cstudy doctor --fix` in Settings, or `not installed` in the status bar | Run `cstudy doctor --fix` once, with the network on, then open the file again |
| `stopped: exit 1` in the status bar | The language server ended: choose **Restart**, or run `cstudy doctor` to check the install |
| `no code intelligence for Java: needs JDK 25 or 26` | jdtls runs only on JDK 25 or 26: select one with `JAVA_HOME` ([Java](editor.md#java)) |
| `no code intelligence for Rust: rust-analyzer is not installed` | Run `rustup component add rust-analyzer` ([Rust](editor.md#rust)) |
| `Docker is not running` in the status bar, on a service project | Start Docker, or run the tests once, which starts it; then choose **Restart** |
| `Ctrl+Space` shows nothing | Autocomplete is off, or code intelligence is: turn both on in Settings. With Autocomplete off the editor offers no completion at all |
