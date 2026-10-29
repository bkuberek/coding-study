# coding-study workspace

Your practice workspace for [coding-study](https://github.com/bkuberek/coding-study): your solutions, notes, attempt history and your own problems. Version it in its own git repository if you like; `cstudy` never commits for you.

## Daily loop

```bash
cstudy next                      # what to practice
cstudy start two-sum --lang python
cstudy test                      # run your code against the cases
cstudy done --rating ok          # finish the attempt and schedule a review
```

Run `cstudy` anywhere inside this directory, or from elsewhere with `cstudy --workspace <path>` or `CSTUDY_WORKSPACE=<path>`.

## Layout

| Path | What it holds |
|------|---------------|
| `python/`, `typescript/`, `jvm/`, `go/`, `rust/` | One practice project per runtime; open this directory, the workspace root, in your IDE ([below](#using-an-ide)). `go/` needs Go 1.24 or newer, only for `--lang go`; `go.work` lets gopls find it from the root. `rust/` needs Rust 1.80 or newer (rustup), only for `--lang rust`; `cstudy start` lists each problem in `rust/Cargo.toml` so rust-analyzer checks it |
| `.vscode/`, `.idea/` | VS Code and IntelliJ IDEA project files written by `cstudy init` and `cstudy ide`; yours to edit |
| `notes/` | Your answers to system design and code review items |
| `problems/` | Problems you write yourself (`cstudy new <slug>`); they join the catalog |
| `.archive/` | Earlier attempts that `cstudy start --fresh` and reviews moved aside |
| `.cs/workspace.toml` | Marks this directory as a workspace; keep it in version control |
| `.cs/ide.json` | Which IDE files cstudy wrote, and what they held; keep it in version control |
| `.cs/`, `.statements/`, `progress.db` | Caches, the runner runtime, rendered statements and your progress; ignored, per machine |

## Using an IDE

Open this directory in VS Code or IntelliJ IDEA: every `cstudy` action is already there as a task or run configuration, in two forms. **Current file** runs on the solution file in the editor (`cstudy test <file>`); **active attempt** runs on your active attempt (`cstudy test`).

| Action | Command |
|--------|---------|
| Test, perf, typecheck (TypeScript), bench, hint | `cstudy test`, `test --perf`, `test --typecheck`, `bench`, `hint` |
| Done | `cstudy done --rating=ok\|easy\|hard` or `--gave-up`: VS Code asks, IntelliJ has one configuration each |
| Solution, show, start (current file only) | `cstudy solution`, `show`, `start --no-open` |
| Workspace | `cstudy next`, `stats`, `doctor` |
| Debug | `cstudy test --debug` with a debugger attached to the runner, so a breakpoint in your solution stops |

The files are yours to edit. After upgrading `cstudy`, run `cstudy ide` to bring them up to date: it rewrites only files still as it wrote them, names the ones you changed (`cstudy ide --force` overwrites them too), and never touches files it did not write, such as a run configuration of your own.

### VS Code

- Run: **Tasks: Run Task**, then a `cstudy …` task.
- Debug Python, TypeScript or Java: set a breakpoint, open the solution, and start **Debug current file (Python)** (or TypeScript, Java) from Run and Debug. Its task starts `cstudy test --debug`, and the debugger attaches once cstudy prints `waiting for debugger`.
- Set up for you: the Python interpreter in `python/.venv`, TypeScript from `typescript/node_modules`, the Gradle import of `jvm/`, Go through `go.work` (tools run with `GOTOOLCHAIN=local`), the Rust project `rust/Cargo.toml` for rust-analyzer, and the recommended extensions (Python, Debugpy, Java, Gradle, Go, rust-analyzer).
- Go and Rust run and test here from the same tasks; debugging them is not set up yet.
- Kotlin runs and tests here but cannot be debugged: the Java debugger never binds Kotlin breakpoints ([vscode-java-debug#241](https://github.com/microsoft/vscode-java-debug/issues/241)). Debug Kotlin in IntelliJ IDEA.

### IntelliJ IDEA

- Run: pick a configuration in the folders `cstudy: current file`, `cstudy: active attempt`, `cstudy: workspace` and `cstudy: debug`. Current-file configurations start a small launcher, `.cs/runtime/ide/cstudy-launcher.jar`, because IntelliJ's shell configurations cannot pass the open file. With no editor focused, they stop with `open a solution file in the editor first`.
- Debug Java or Kotlin: set a breakpoint, then **Debug** (not Run) **Debug current file (Java, Kotlin)**. It starts **Debug JVM (listen)**, which waits on port 5005, and `cstudy test --debug --debug-connect`, whose JVM connects to it. The listener restarts itself, so you can keep it running and debug again.
- Set up for you: the project JDK `21` (`.idea/misc.xml`) and the Gradle project `jvm/`, run with that JDK (`.idea/gradle.xml`).
- Go and Rust run here from the same run configurations; open the workspace root with the Go or Rust plugin (GoLand and RustRover include them); `cstudy` writes no IntelliJ project files for them.
- Python and TypeScript run here, but debugging them is not set up: Python needs the Python plugin, and attaching to Node needs IntelliJ IDEA Ultimate. Debug them in VS Code.

### Once, by hand

| What | How |
|------|-----|
| A JDK 21 named `21` | IntelliJ: accept the prompt to set up the missing SDK `21`, or add one in **Project Structure > SDKs**. IDE-wide SDKs cannot come from project files |
| Load the Gradle project | IntelliJ: click **Load Gradle Project** when it offers to |
| Python in IntelliJ | With the Python plugin, add `python/.venv` as the module's SDK |
| Python in VS Code | Run `cstudy doctor --fix` first so `python/.venv` exists; on Windows pick `python\.venv\Scripts\python.exe` with **Python: Select Interpreter** |
| A JDK for VS Code | The Java extension needs a JDK 21 (`JAVA_HOME`, or its own setting); the workspace does not pin one, since its path differs per machine |

## On a new machine

After cloning this workspace, install `cstudy` and run `cstudy doctor --fix` here: it recreates the runner runtime in `.cs/runtime/` (with the IntelliJ launcher), the Python venv, `node_modules` and the Gradle build. Progress lives in `progress.db`, which is not committed; `cstudy export` writes `progress-export.json`, which you may commit, and `cstudy import` restores it.
