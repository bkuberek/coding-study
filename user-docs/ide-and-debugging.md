---
title: Your IDE and the debugger
summary: The VS Code and IntelliJ IDEA files cstudy writes, other editors with cstudy test --watch, how cstudy ide keeps your edits, how to debug a run with cstudy test --debug, and common editor problems.
section: Practise
order: 75
---

# Your IDE and the debugger

`cstudy init` writes project files for VS Code and IntelliJ IDEA, so that the workspace root opens with every `cstudy` action ready to run and debug. Open the workspace root, not one language's folder. `cstudy` stays the judge: the IDE runs `cstudy` commands, and its debugger attaches to the run that `cstudy test --debug` starts.

Each action comes in two forms. **Current file** runs on the solution file in the editor, as `cstudy test <file>` does; **active attempt** runs on the attempt you used last, as `cstudy test` does.

| Action | Current file | Active attempt |
|--------|:------------:|:--------------:|
| `test`, `test --perf`, `test --typecheck` (TypeScript), `bench`, `hint` | yes | yes |
| `done` with a rating, or `--gave-up` | yes | yes |
| `solution`, `show`, `start --no-open` | yes | no |
| `test --debug` | yes | yes |
| `next`, `stats`, `doctor` | for the whole workspace | |

## VS Code

| File | Holds |
|------|-------|
| `.vscode/tasks.json` | A task per action, such as **cstudy test (current file)**; run one with **Tasks: Run Task**. The `done` tasks ask how it went |
| `.vscode/launch.json` | **Debug current file** and **Debug active attempt** for Python, TypeScript, Java, Go and Rust. Each starts its `cstudy test --debug` task, then attaches once the run waits for it |
| `.vscode/settings.json` | The Python interpreter in `python/.venv`, TypeScript from `typescript/node_modules`, the Gradle import of `jvm/`, the Go tools run with `GOTOOLCHAIN=local`, and rust-analyzer pointed at `rust/Cargo.toml` and each Rust project folder. No JDK path, since it differs per machine |
| `.vscode/extensions.json` | Recommends the Python, Debugpy, Java, Gradle, Go, rust-analyzer and CodeLLDB extensions |

To debug, set a breakpoint in your solution, then start **Debug current file (Python)**, or the configuration of your language, from Run and Debug.

| Language | What to know |
|----------|--------------|
| Python | Run `cstudy doctor --fix` first, so that `python/.venv` exists with `debugpy` in it |
| Java | The Java extension needs a JDK 21 to 26, from `JAVA_HOME` or its own setting |
| Kotlin | Runs and tests here, but cannot be debugged: VS Code's Java debugger never stops at Kotlin breakpoints. Debug Kotlin in IntelliJ IDEA |
| Go | Needs Delve ([Go](toolchains.md#go)) |
| Rust | Needs the CodeLLDB extension and LLDB's debug server ([Rust](toolchains.md#rust)) |

## IntelliJ IDEA

| File | Holds |
|------|-------|
| `.idea/runConfigurations/` | Run configurations in four folders: `cstudy: current file`, `cstudy: active attempt`, `cstudy: workspace` and `cstudy: debug` |
| `.idea/misc.xml` | The project JDK, named after the JDK your shell selects, such as `26`, or `25` when none is found, and the language level the build uses |
| `.idea/gradle.xml` | `jvm/` as a Gradle project, with its `java` and `kotlin` modules, run with the project JDK |

The current-file configurations start the launcher, `.cs/runtime/ide/cstudy-launcher.jar`, because IntelliJ IDEA's shell configurations cannot pass the open file. It runs `cstudy` with the same arguments and exits as `cstudy` does. It looks for `cstudy` in `CSTUDY_EXECUTABLE`, then on `PATH`, then where uv and other tools install programs, such as `~/.local/bin`. If it finds none, set `CSTUDY_EXECUTABLE` to the path of `cstudy`. With no editor focused, a current-file configuration stops with `open a solution file in the editor first`.

To debug Java or Kotlin, set a breakpoint, then **Debug**, not Run, **Debug current file (Java, Kotlin)**. It starts **Debug JVM (listen)**, which listens on port 5005, and `cstudy test --debug --debug-connect`, whose JVM connects to it. The listener starts again after each session, so you can leave it running.

| Once, by hand | How |
|---------------|-----|
| The project JDK | Accept the prompt to set up the missing SDK that `.idea/misc.xml` names, or add a JDK of that release under that name in **Project Structure > SDKs** |
| The Gradle project | Click **Load Gradle Project** when it offers to |
| Python | With the Python plugin, add `python/.venv` as the module's SDK |
| After you switch JDKs | Run `cstudy ide idea`: it updates the project JDK while `misc.xml` is as `cstudy` wrote it, and keeps it, saying so, once you or IntelliJ IDEA changed it |

Go and Rust run from the same run configurations; open the workspace root with the Go or Rust plugin. `cstudy` writes no IntelliJ IDEA project files or debug configurations for Go and Rust, and none for Python and TypeScript, whose debugging needs the Python plugin, or IntelliJ IDEA Ultimate for Node. Debug those languages in VS Code, or with any debugger that attaches to the [debug port](#debug-ports).

## Other editors

`cstudy` writes project files only for VS Code and IntelliJ IDEA, and any other editor works too: each language's folder of the workspace is an ordinary project that its language server finds.

| Language | Point your editor at |
|----------|----------------------|
| Python | The interpreter `python/.venv/bin/python`, which `cstudy doctor --fix` creates |
| TypeScript | The TypeScript of `typescript/node_modules`, which `cstudy doctor --fix` installs |
| Java, Kotlin | The Gradle build in `jvm/`, on a JDK 21 to 26 |
| Go | The workspace root, whose `go.work` names `go/`; run the Go tools with `GOTOOLCHAIN=local`, as `cstudy` does |
| Rust | `rust/Cargo.toml`, or open `rust/` itself |

In Neovim, or another editor in a terminal, keep `cstudy test --watch` running in a split or a second terminal:

```bash
cstudy start two-sum --no-open    # write the files without opening an editor
cstudy test --watch               # run now, then after every save
```

`cstudy test --watch` runs the cases at once, then again each time you save your solution: for Java and Kotlin, any file of the problem's package, and for a project, any file of its folder apart from dependencies, caches and build output. It clears the screen before each run, reports a compile error and keeps watching, and ends with `Ctrl+C`. A save that changes nothing runs nothing, and an editor that saves by writing a new file and renaming it over the old one is seen like any other. A service project's `cstudy test` takes no flags, so it has no `--watch`.

With `EDITOR=nvim`, `cstudy start` opens your solution and the statement in Neovim itself, unless you pass `--no-open` or set `open_on_start = false` ([configuration keys](commands.md#configuration-keys)). To debug, start `cstudy test --debug` in the terminal and attach your editor's debugger to the [debug port](#debug-ports).

## Your edits and cstudy ide

The IDE files are yours to edit. `cstudy ide` writes them again, for a workspace made before a file existed, or after an upgrade:

```bash
cstudy ide             # both IDEs
cstudy ide vscode      # or idea
cstudy ide --force     # also overwrite the files you edited
```

`.cs/ide.json`, the manifest, records what `cstudy` wrote in each file. Keep it in version control with the IDE files, as the workspace's `.gitignore` does, so that a clone knows which files are still as `cstudy` wrote them.

| A file | `cstudy ide` |
|--------|--------------|
| Missing | Writes it |
| As `cstudy` wrote it | Writes the new version |
| Edited, or not written by `cstudy` | Keeps it, and says so; `--force` overwrites it |
| No longer generated by this `cstudy` | Deletes it while it is as `cstudy` wrote it; once edited, keeps it |
| Not one `cstudy` generates, such as a run configuration of your own | Never touches it |

```text
ide      vscode, idea · 1 kept
warning  kept .vscode/settings.json: edited, or not written by cstudy (cstudy ide --force overwrites it)
```

To keep your edits and get a new setting too, copy the new keys into your file by hand. `cstudy doctor --fix` never writes IDE files.

## Debug a run

`cstudy test --debug` runs your code as `cstudy test` does, with the runner waiting for your debugger, so a breakpoint in your solution stops the real run. The verdict comes when the run ends.

```bash
cstudy test --debug                        # the active attempt
cstudy test two-sum --debug --lang java
cstudy test --debug --debug-port 5679      # another port
cstudy test --debug --debug-connect        # Java and Kotlin: connect to a debugger that listens
```

Once the debugger can attach, it prints one line to standard error, which the IDE configurations wait for:

```text
cstudy: waiting for debugger on 127.0.0.1:5678 (python)
cstudy: connecting to debugger at 127.0.0.1:5005 (kotlin)
```

The second form is `--debug-connect`, for a debugger that already listens, such as IntelliJ IDEA's **Debug JVM (listen)**.

| Rule | Detail |
|------|--------|
| Time limits off | No time limit applies, and the runner is never restarted, so a run can wait at a breakpoint as long as you need. The report shows no durations |
| Not recorded | A debug run is not stored: it never counts as a pass and opens no level. Run `cstudy test` again to record one |
| Cannot combine | `--debug` refuses `--watch`, `--json`, `--events`, `--perf`, `--stress`, `--seed` and `--time-limit`, with exit 3. `--no-time-limit` is accepted |
| Its own flags | `--debug-port <port>` sets the port, 1 to 65535. `--debug-connect` is for Java and Kotlin only. Both need `--debug` |
| Concurrent problems | Only the sequential cases run: stress runs are skipped while debugging |
| Project problems | Breakpoints stop in your project's code and in its tests. Go debugs one package's tests. Rust debugs one test: the first that `--case` selects, or the first of the suite. `--debug-connect` is not available |
| Service projects | `cstudy test --debug` is not available: run `cstudy dev --debug` and attach to the address it prints ([your own IDE and debugger](service-projects.md#your-own-ide-and-debugger)) |
| Stop | `Ctrl+C` ends the run and frees the port |

## Debug ports

The debugger listens on 127.0.0.1 only, never on another interface.

| Language | Debugger | Default port | `--debug-connect` |
|----------|----------|-------------:|:-----------------:|
| Python | debugpy, in `python/.venv` | 5678 | no |
| TypeScript | Node's inspector | 9229 | no |
| Java | The JVM's debug agent | 5005 | yes |
| Kotlin | The JVM's debug agent | 5005 | yes |
| Go | Delve | 2345 | no |
| Rust | `debugserver` on macOS, `lldb-server` on Linux | 12345 | no |

The IDE configurations use these ports. If you pass another with `--debug-port`, attach to that port instead. When something already listens on the port, the run stops with exit 4: `cannot debug python: port 5678 on 127.0.0.1 is already in use; stop the other debug session or choose another port with --debug-port`.

## Common editor problems

| You see | Do |
|---------|----|
| rust-analyzer reports an outdated toolchain, or flags standard macros such as `todo!` and `vec!` | Run `rustup update`: the editor's rust-analyzer needs a recent stable toolchain |
| rust-analyzer cannot show the standard library | Run `rustup component add rust-src` ([Rust](toolchains.md#rust)) |
| VS Code shows no Rust errors at all, in a workspace an older `cstudy` set up | Remove `"rust-analyzer.check.extraArgs": ["--keep-going"]` from `.vscode/settings.json`, or run `cstudy ide --force` |
| Python imports do not resolve, or no Python interpreter is selected | Run `cstudy doctor --fix`, which creates `python/.venv`, then select `python/.venv/bin/python` as the interpreter if your editor has not |
| TypeScript cannot find the workspace's packages | Run `cstudy doctor --fix`, which installs `typescript/node_modules` |
| Go files show no errors, or say they are outside a module | Open the workspace root, whose `go.work` names `go/` |
| Your editor's `go` downloads a Go toolchain | Run the Go tools with `GOTOOLCHAIN=local`. The workspace's VS Code files do, and `cstudy ide` adds them to an older workspace |
| The Java extension finds no JDK | Give it a JDK 21 to 26, through `JAVA_HOME` or its own setting |
| IntelliJ IDEA names a missing SDK, or the wrong one after you switched JDKs | Accept its prompt, or add a JDK of that release under that name; after a switch, run `cstudy ide idea` |
| Kotlin breakpoints never stop in VS Code | VS Code's Java debugger does not stop in Kotlin: debug Kotlin in IntelliJ IDEA |
| A current-file action says `open a solution file in the editor first` | Click into your solution file, then run the action again |
| The IntelliJ IDEA launcher finds no `cstudy` | Set `CSTUDY_EXECUTABLE` to the path of `cstudy` |
| A setting that a newer `cstudy` writes is missing from your IDE files | `cstudy ide` keeps the files you edited, and says so: copy the new keys in by hand, or run `cstudy ide --force` |
