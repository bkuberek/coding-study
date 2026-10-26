# ADR 0010: IDEs run cstudy and attach to its runner

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-26 |
| Spec | [installation-and-workspaces](../specs/installation-and-workspaces.md#ide-files), [cli](../specs/cli.md#cstudy-ide) |

## Context

Practice happens in the IDE, but a workspace shipped no editor configuration: every action needed the terminal, and a breakpoint in a solution could never stop, because user code runs in a runner subprocess under a hang guard. The owner wants `cstudy init` to create a workspace that opens in IntelliJ IDEA and VS Code with run configurations for every `cstudy` action on the current solution file, debugging included, and with SDKs and interpreters set up wherever project files can set them.

Two spikes established what the IDEs allow:

- A debug agent attaches headlessly to the real runner in all four languages (debugpy for Python, the Node inspector with `--inspect-wait` on type-stripped `.ts` files, which keeps lines and columns, and JDWP for Java and Kotlin), and a runner paused at a breakpoint never times out.
- IntelliJ Shell Script configurations expand no macros, so they cannot pass the file in the editor; JAR Application configurations expand `$FilePath$` in their program parameters, and Gradle configurations do not. With no editor focused, `$FilePath$` is the project directory.
- IntelliJ's Remote JVM Debug configuration can listen and restart itself after each session; compound configurations start their parts without ordering. Attaching to Node is IntelliJ IDEA Ultimate only, and Python debugging needs a plugin with its own agent.
- VS Code's Java debugger never binds Kotlin breakpoints ([vscode-java-debug#241](https://github.com/microsoft/vscode-java-debug/issues/241)).

## Decision

- `cstudy` stays the judge. IDE configurations run `cstudy` commands, on the file in the editor or on the active attempt, and never run user code themselves. Debugging runs `cstudy test --debug`, which starts the real runner with its debug agent on 127.0.0.1 and no hang guard, and the IDE attaches to that runner.
- One catalog of actions (`domain/ide_actions.py`) is rendered into `.vscode/` and `.idea/` by one adapter per IDE, so an action added to the catalog reaches both. Tests parse every rendered command line with the real command line.
- VS Code: `process` tasks run `cstudy <action> ${file}`; `done` asks for its outcome through a `pickString` input. Each debug configuration (Python with debugpy, TypeScript with node, Java with java) first runs `cstudy test --debug` as a background task whose problem matcher ends at cstudy's `waiting for debugger` line, then attaches. Kotlin gets tasks only.
- IntelliJ: current-file configurations are JAR Application configurations that start a launcher jar, which runs `cstudy` with their arguments, standard streams and exit code. The jar is built reproducibly from `tools/ide-launcher/`, shipped in the package, and copied into `.cs/runtime/ide/` by every runtime refresh, so `cstudy doctor --fix` restores it in a fresh clone. Active-attempt and workspace actions are Shell Script configurations run in the terminal.
- IntelliJ debugs Java and Kotlin in listen mode: **Debug JVM (listen)** waits on port 5005 and restarts after each session, and a compound starts it together with `cstudy test --debug --debug-connect`, whose JVM connects to it; cstudy retries the connection for about 10 s because the compound does not order its parts.
- SDKs: `.idea/misc.xml` names the project JDK `21`, the practice projects' toolchain, and `.idea/gradle.xml` links `jvm/` run with that JDK; `.vscode/settings.json` points at `python/.venv` and `typescript/node_modules/typescript`. SDK definitions that IDEs keep per user stay manual and are listed in the workspace README.
- Generated files are the user's to edit. `.cs/ide.json`, tracked with them, records the digest of each file cstudy wrote; regenerating overwrites only files that are missing or still as written, keeps the others with a warning until `--force`, and never touches files cstudy did not write.

## Consequences

- A fresh workspace opens with every action one click away in both IDEs, and a breakpoint stops in the code cstudy judges, with the same cases, comparators and progress as the terminal.
- The package ships a 3.7 KB binary. It is reproducible with javac 21 (javac 17 emits other bytes for the same `--release 17`), and a slow test rebuilds it and compares the bytes; changing the launcher means running `tools/ide-launcher/build.sh` and committing the jar.
- IntelliJ users need a JDK to run the launcher, which the JVM projects need anyway. The open-file configurations fail with "unable to access jarfile" until the runtime exists, that is, until `cstudy doctor --fix`, `cstudy ide` or any run on a fresh clone.
- IntelliJ rewrites `misc.xml` and `gradle.xml` when it imports the project; `cstudy ide` then keeps them and says so, which is the rule working as intended.
- Debugging is one configuration per language in VS Code (Kotlin excluded) and one compound for both JVM languages in IntelliJ (Python and TypeScript excluded); each IDE covers the other's gaps.
- The debug actions depend on the `--debug` options of `cstudy test` and on the name **Debug JVM (listen)**, which `cstudy test --debug --debug-connect` quotes when nothing listens.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| IDE-native test configurations (pytest, JUnit, Node test runner) | They judge with their own harness, not cstudy's cases, comparators, time limits and progress: a second source of truth |
| Debug the solution by launching it directly from the IDE | The code under the debugger would not be what cstudy runs and judges, and no case data reaches it |
| IntelliJ Shell Script or Gradle configurations for the current file | Neither expands `$FilePath$` |
| A launcher script instead of a jar | It would need a Shell Script configuration, which expands no macros, or an interpreter configuration per operating system; the jar runs on the JDK the JVM projects already need |
| Build the launcher at `cstudy init` or on first use | Every machine would need `javac` before its first IntelliJ run; the committed jar is small and checked against a rebuild |
| Commit the launcher into the workspace (`.idea/`) | A binary in the user's repository that goes stale on upgrades; the runtime copy refreshes with `cstudy` |
| IntelliJ attach mode, with the runner's JVM listening | Every run needs a second click once cstudy is waiting; listen mode with auto restart is one click and stays ready between runs |
| Kotlin debugging in VS Code | Breakpoints never bind (vscode-java-debug#241), and the community Kotlin extension is deprecated |
| Python and TypeScript debugging in IntelliJ | Node attach is Ultimate only; Python debugging needs a plugin whose agent is not debugpy |
| Overwrite the IDE files on every run | Destroys the user's edits; the manifest makes regenerating safe |
| An ignored manifest, or markers inside the files | An ignored manifest leaves a clone unable to tell cstudy's files from the user's; JSON allows no markers, and IntelliJ drops XML comments when it saves |
