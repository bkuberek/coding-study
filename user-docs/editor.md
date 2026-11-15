---
title: The editor and code intelligence
summary: Edit and save in the web UI, and turn on live errors, hover documentation, go to definition and completion from language servers on your computer.
section: The web UI
order: 110
---

# The editor and code intelligence

The Attempt view of [the web UI](web-ui.md) has an editor over your files. It saves only when you ask, follows changes made in your IDE, and can show what an IDE shows, from language servers on your computer, once you turn that on.

## Edit and save

Open a file by choosing it in the tree; each opens in a tab of its own.

- **Saving.** `Cmd+S`, the **save** button at the end of the tab bar, or `:w` with Vim on saves the active tab. A run saves every tab with unsaved edits first, so it always tests what you see; the page saves at no other time. A tab with unsaved edits shows a dot in place of its close button.
- **Changes from elsewhere show up.** When your IDE or the terminal changes a file, a tab without unsaved edits takes the new version in place and keeps your cursor. A tab with unsaved edits shows a banner instead: **Reload theirs** drops your edits, **Overwrite** saves yours over the file.
- **Leaving asks first.** Closing a tab, leaving the view or closing the page with unsaved edits asks before anything is lost.
- **Generated test files** of a project are editable, as in the terminal, but editing one never changes a grade.
- **Indentation follows the language.** Four spaces in Python, Java, Kotlin and Rust, a tab in Go, two spaces in TypeScript and everything else. `Enter` lands on the right column, one level in after `def f():` or a `{`, and at the previous line's indentation where the language has no rule. `Tab` indents the line by one level.

The editor highlights Python, TypeScript, Java, Kotlin, Go, Rust, JSON, TOML and Markdown. Errors from a run show as underlines and gutter markers on the lines they name. Turn on [code intelligence and autocomplete](#code-intelligence-and-autocomplete) for live errors, documentation on hover, go to definition and completion; until you do, the editor offers no completion list at all.

## Code intelligence and autocomplete

Two settings give the editor what an IDE gives: errors as you type, documentation, jumps to definitions, and completion. They use language servers that run on your computer, and both are off by default, so the editor stays as plain as a notepad until you turn them on.

| Setting | What it does |
|---------|--------------|
| Code intelligence | Live errors, warnings and unused code; documentation when you hover; go to definition into your files and into read-only library sources |
| Autocomplete | Completion as you type or with `Ctrl+Space`, and signature help when you open a call |

**Autocomplete controls all completion.** With it off, the editor offers no completion list and no signature help, not even the basic completion of earlier versions of the page. That is the reason for the setting: you can practise recalling names and signatures with nothing to prompt you, and turn the help on when you want it. Closing brackets as you type is not completion and stays.


## Turn them on

1. Choose **Settings**, check **Code intelligence** and choose **Save**. **Autocomplete** is greyed out with `Turn on code intelligence first` until you check it; it keeps its choice if you turn code intelligence off, and does nothing until both are on.
2. Install the language servers once. In the terminal, run:

   ```bash
   cstudy doctor --fix
   ```

   (or choose **Fix** in the Health view, on the row of each language or at the top). This installs the Python and TypeScript servers into `.cs/lsp/` in your workspace, plus jdtls for Java, a download checked by its SHA-256, and gopls for Go, built with your Go, and needs the network that one time. Kotlin's server comes under a licence you accept first ([Kotlin](#kotlin)). rust-analyzer comes with your Rust toolchain instead ([Rust](#rust)). After that practice needs no internet: nothing else is downloaded and no server reaches the network. Deleting `.cs/lsp/` is safe; `--fix` installs it again. With **Code intelligence** off, `--fix` installs nothing for the editor and says so (`skipped the language servers: code intelligence is off; turn it on in Settings…`), unless the servers are installed already.
3. Check the result. `cstudy doctor` shows a row per language while code intelligence is on, and the Settings view lists each language's state:

   ```text
   ok    code intelligence python basedpyright 1.40.2
   ok    code intelligence typescript typescript-language-server 6.0.3
   ok    code intelligence java jdtls 1.63.0
   ok    code intelligence kotlin kotlin-lsp 263.7084.0, runs until 2026-11-12
   ok    code intelligence go gopls 0.24.0
   ok    code intelligence rust rust-analyzer 1.91.0
   ```

4. Open a file. The status bar under the editor shows `python · basedpyright · ready` when its server is up, and **Restart** if it stopped.

If a server is not installed, or starts slowly, the editor works as it does without code intelligence, and with Autocomplete on it falls back to the editor's own basic completion until the server is ready.

While code intelligence is on, `cstudy serve` starts the server of your default language (Settings, **Default language**) as it starts, so the first practice file you open in that language has its server ready, which matters most for Java and Kotlin. It starts no other language's, and it stops after a while if no editor takes it over.

## What you see

- **Errors and warnings.** They are underlined shortly after you stop typing (Rust's compiler errors after each save), with a marker in the gutter and counts in the status bar. Unused code fades, deprecated code is struck through, and hints get no underline. The errors of your last run stay, marked `last run`, and a run error that the server repeats shows once.
- **Hover documentation.** Rest the pointer on a name, or press the keys below, to read its type and documentation. An error on that name shows above the documentation. A link in the documentation to a library file, as Go's documentation has, opens that file in a library tab at the line it names.
- **Go to definition.** A name in your own file jumps within it; a name from another file of the attempt opens that file's tab; a name from the standard library or a package opens a **library** tab, read-only, with the file's path beside the code. A library tab cannot be saved, and closing it loses nothing. `Ctrl+-` goes back to where the jump started.
- **Reference solutions stay hidden.** A definition never opens a reference solution, and the servers cannot read the folders that hold them: an import of one fails as an import of a missing file. You see a solution only through **Solution…**, and its question.


## Autocomplete in the editor

- **Completion.** The list opens as you type a name or a `.`, and with `Ctrl+Space`. Move with the arrows, accept with `Enter` or `Tab`, close with `Escape`. The selected item's documentation shows beside the list. Accepting inserts plain text: no snippets with placeholders, and no imports added for you.
- **Signature help.** Typing `(` or `,` in a call shows the signature with the current parameter in bold. `Cmd+Shift+Space` opens it inside a call.


## Keys and mouse

Read `Ctrl` for `Cmd` on Linux and Windows. These work while code intelligence applies to the file, except where the last column says otherwise.

| Do | Keys or mouse | With Vim, in normal mode |
|----|---------------|--------------------------|
| Go to definition | `Cmd`-click on macOS, `Ctrl`-click elsewhere, or `F12` | `gd`, `Ctrl+]`; the click and `F12` work too |
| Back to where the jump started | `Ctrl+-` | `Ctrl+o` |
| Hover documentation | Rest the pointer; or `Cmd+K` then `Cmd+I`; `Escape` closes it | `K` |
| Next and previous error | `F8` and `Shift+F8`, skipping hints | `]d` and `[d` |
| List the file's errors | `Cmd+Shift+M` | The same |
| Completion (Autocomplete on) | Type, or `Ctrl+Space`; on macOS also `` Option+` `` and `Option+I`, since macOS may take `Ctrl+Space` for its input sources | In insert mode the same; `Escape` closes the list and leaves insert mode |
| Signature help (Autocomplete on) | `(` or `,` in a call, or `Cmd+Shift+Space` | In insert mode the same |
| Add a second cursor, with the settings on or off | `Alt+Shift`-click (`Option+Shift`-click on macOS) | The same |

`Cmd`-click and `Ctrl`-click never add a cursor any more: with code intelligence on they go to the definition, and with it off they are a plain click. Adding a cursor is `Alt+Shift`-click in both modes, so turning a setting on or off never changes what a click does to your selection.

## Languages

| Language | Server | State |
|----------|--------|-------|
| Python | basedpyright | Available |
| TypeScript | typescript-language-server | Available |
| Java | jdtls | Available, on JDK 25 or 26 |
| Kotlin | kotlin-lsp | Available once you accept its licence, with a JDK from 21 to 26 |
| Go | gopls | Available, built by `cstudy doctor --fix` with your Go |
| Rust | rust-analyzer | Available, once you run `rustup component add rust-analyzer` |

A file in a language without a server shows a one-line notice in the status bar and works as it does without code intelligence. A language's state also shows in Settings.

## Java

Java's server, jdtls, is a Java program: it runs on the JDK that `cstudy` selects (`JAVA_HOME`, or the `java` on your `PATH`), and only when that JDK is 25 or 26. JDK 25 is the one to install. With another JDK, the status bar says `no code intelligence for Java: needs JDK 25 or 26 · Health`, Settings says `needs JDK 25 or 26`, and `cstudy doctor` names the JDK it found and how to select another:

```text
WARN  code intelligence java jdtls needs JDK 25 or 26, not 21.0.5
      fix: select a JDK 25 to 26 with JAVA_HOME, or install JDK 25: …
```

`cstudy doctor --fix` downloads jdtls whatever JDK you have, so installing JDK 25 later needs no network.

- **The first start takes a while.** jdtls imports the `jvm/` Gradle build, or your project folder's, before it reports: quickly when a Gradle daemon is running, and longer when it has to start one. The status bar says `java · jdtls · ready` meanwhile, and errors show once the import is done, then shortly after you stop typing. A tab you close keeps its server for a few minutes, so coming back is quick.
- **It needs no network,** over what `cstudy doctor --fix` warmed up: the Gradle import runs with no network and nothing is downloaded, not even the checksums of the Gradle wrapper, which jdtls would otherwise fetch.
- **It leaves your folders as they were.** No `.project`, `.classpath`, `.settings/` or `bin/` appears in `jvm/` or a project folder: jdtls checks your files as you type without building them, and keeps its index in `.cs/lsp/jdtls-data/`, one per folder.
- **Memory.** A Java session needs a good share of memory, under a fixed heap, and its first import may start a Gradle daemon that stays idle afterwards, as the one `cstudy test` starts does.
- **Definitions into the JDK.** A class of the JDK or of a library, such as `ArrayList`, has no file of its own: a Cmd-click on it shows a note, `java.base/java.util/ArrayList.java:169 · not a file: URI`, and hover still shows its documentation. Your project's files and the runner's support code open in tabs, as in Python.

## Kotlin

Kotlin's server is kotlin-lsp, the Kotlin analysis of a well-known Kotlin IDE behind the same protocol. It is partly closed source and comes under its own [licence agreement](https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt), so `cstudy doctor --fix` downloads it only once you accept that licence. It fetches the newest build each time it runs, checked against the SHA-256 published beside it, and downloads nothing when the newest is the one you have. Read the licence, then either answer `y` when `--fix` asks at a terminal, or say so up front:

```bash
cstudy doctor --fix --accept-license kotlin-lsp
```

Your acceptance is recorded in the workspace's `.cs/workspace.toml`, so `--fix` asks again in this workspace only if a newer build comes under a new version of the agreement. Until you accept, `--fix` downloads nothing for Kotlin and says how to accept (the Health view's **Fix** never accepts for you), the status bar says `no code intelligence for Kotlin: kotlin-lsp's license is not accepted · Health`, and the Kotlin row of `cstudy doctor` is a `WARN` whose fix is `cstudy doctor --fix --accept-license kotlin-lsp`.

- **The download is large.** The archive for your machine comes with its own Java runtime. It is the largest download of any language server and takes over 1 GB on disk in `.cs/lsp/kotlin-lsp/`, plus an index per folder in `.cs/lsp/kotlin-lsp-data/`.
- **`--fix` warms it up once, with the network.** After the Gradle warm-up, `--fix` runs the server on `jvm/` until its index is built: the import fetches the sources of the Kotlin standard library and the other libraries into Gradle's cache, which hover documentation and definitions read later. After that it needs no network: no update check, and no data leaves your computer.
- **The first start takes a while.** It imports the `jvm/` Gradle build, or your project folder's, and indexes it before it reports, longer on a busy machine. The status bar says `kotlin · kotlin-lsp · ready` meanwhile; errors show once it is done. A tab you close keeps its server for a few minutes.
- **It needs a JDK.** The server runs on its own runtime, but imports your build with the JDK that `cstudy` selects, which must be one cstudy supports, 21 to 26.
- **Memory.** A Kotlin session uses around 2 GB of memory, the most of any language, plus the Gradle daemon its import may start.
- **Definitions into the standard library.** A function such as `mutableListOf` lives in a sources jar: a Cmd-click on it shows a note naming the jar and the file, and hover shows its documentation. Your project's files open in tabs.
- **It leaves your folders as they were,** apart from Gradle's own `.gradle/`, as `cstudy test` leaves it.
- **Each build stops a few weeks after its release.** kotlin-lsp ships as early-access builds that stop working once their built-in licence ends, and a new one comes out every few weeks. `cstudy doctor` shows the last day of yours, `ok    code intelligence kotlin kotlin-lsp 263.7084.0, runs until 2026-11-12`, and warns in its last week. Run `cstudy doctor --fix` with the network then: it fetches the newest build if there is one, and says the one you have is the newest otherwise. Once a build has stopped, `cstudy doctor`, Settings and the status bar say `expired on 2026-11-13: run cstudy doctor --fix`, and Kotlin files work as without code intelligence until `--fix` fetches a newer one.

## Go

Go's server is gopls. `cstudy doctor --fix` builds it once with `go install` into `.cs/lsp/bin/`, with the network, with the Go you selected and no other: the gopls version follows your Go, v0.21.1 on Go 1.25, v0.23.0 on 1.26 and v0.24.0 on 1.27. After you upgrade Go, `cstudy doctor` says so and `--fix` builds the matching gopls:

```text
WARN  code intelligence go gopls 0.23.0 installed; cstudy needs 0.24.0
      fix: cstudy doctor --fix
```

- **Errors show shortly after you stop typing,** with unused imports and variables faded: Go refuses to build them, so gopls marks them as errors too.
- **It needs no network.** gopls loads your packages with `GOTOOLCHAIN=local` and `GOPROXY=off`, as `cstudy test` builds them, and shows no links to pkg.go.dev.
- **Links in the documentation open the standard library.** Hovering `strings.Split` shows its documentation, and a name in it, such as `Cut`, is a link: choose it to open GOROOT's source in a library tab at that function.

## Rust

Rust's server is rust-analyzer, which comes with your Rust toolchain. `cstudy doctor --fix` never changes the toolchain, so add it yourself once:

```bash
rustup component add rust-analyzer
```

Until you do, the status bar says `no code intelligence for Rust: rust-analyzer is not installed · Health`, and `cstudy doctor` names the command. Any `rust-analyzer` on your `PATH` whose `--version` runs is used, whichever version it is.

- **Two kinds of errors.** rust-analyzer's own, such as a syntax error, show as you type. The compiler's, from `cargo check`, such as an unknown name or a type error, show once the project is loaded and after each save, with unused variables faded. `cargo check` runs offline, into `target/rust-analyzer/`, so it never waits for your IDE's.
- **The first load.** rust-analyzer loads your project first, which takes longer the first time; the page asks for its errors again until it is ready.
- **The standard library opens from `.cs/lsp/rust-library/`.** A Cmd-click on `Vec` or `len` opens the toolchain's source through links cstudy makes there, so rust-analyzer reads it offline whatever the workspace's vendored crates say.
- **It runs your build scripts.** Like `cargo test`, rust-analyzer runs build scripts and procedural macros of the code you open.

