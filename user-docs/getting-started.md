---
title: Getting started
summary: Install cstudy, create a workspace, and solve your first problem in your own editor.
section: Start here
order: 10
---

# Getting started

`cstudy` is a study tool for everyone who writes code, from beginners to experts. You solve original problems in your own editor, in Python, TypeScript, Java, Kotlin, Go or Rust, and `cstudy` tests your code, checks whether it is fast enough, shows reference solutions, and brings each problem back for review when you are about to forget it. Everything runs on your computer, with no account.

The problems cover algorithms and data structures, practical tasks that grow over several levels, object-oriented design, concurrency, debugging, system design, code review, security and AI. Short guides teach each idea before you practise it.

## Install cstudy

With Homebrew, on macOS or Linux:

```bash
brew install bkuberek/tap/cstudy
cstudy --version
```

Homebrew also installs the Python that `cstudy` runs on. Upgrade with `brew upgrade cstudy`. Recent versions of Homebrew ask you to trust a tap before some commands read it: run `brew trust bkuberek/tap` once if it asks.

Or with uv or pipx, from the source repository:

```bash
uv tool install git+https://github.com/bkuberek/coding-study
# or: pipx install git+https://github.com/bkuberek/coding-study
```

Upgrade with `uv tool upgrade coding-study`, or `pipx upgrade coding-study`.

Keep one of these installs. When there are several, the `cstudy` that comes first on your `PATH` runs: `which -a cstudy` lists them, and `cstudy doctor` warns and gives the command that removes each extra copy.

After an upgrade, run `cstudy doctor --fix` in your workspace. [Upgrading cstudy](upgrading.md) says what it refreshes and what stays yours.

## Install the language toolchains

`cstudy` runs your code with the real toolchain of each language, which you install yourself. uv and Python 3.13 are required. Node.js and pnpm (TypeScript), a JDK (Java and Kotlin), Go and Rust are needed only for the languages you practise. [Install the language toolchains](toolchains.md) has the steps for macOS and Linux.

## Create your workspace

You practise in a **workspace**: a folder of your own for your solutions, notes and progress. Create one, then let `cstudy doctor --fix` set up its projects:

```bash
cstudy init ~/cstudy-workspace --git   # --git runs git init; cstudy never commits
cd ~/cstudy-workspace
cstudy doctor --fix                    # uv sync, pnpm install, Gradle warm-up, runner checks
```

`cstudy doctor` checks each tool and prints a fix for anything missing ([check your setup](doctor.md)). A missing Node.js, pnpm or JDK shows as `FAIL` and a missing Go or Rust as `WARN`; the other languages still work. [Your workspace](workspace.md) explains what is in the folder.

## Solve your first problem

1. Pick a problem. `cstudy next` suggests one and prints the command that starts it:

   ```bash
   cstudy next
   cstudy start two-sum                 # add --lang typescript, java, kotlin, go or rust
   ```

   `cstudy start` writes a stub for your code and the problem's statement, then opens both in your editor (`$VISUAL` or `$EDITOR`).

2. Open the language's project folder of the workspace in your IDE, such as `python/` or `typescript/`, or open the workspace root. Its language server then works with no extra setup.

3. Write your solution, and run the tests on every save:

   ```bash
   cstudy test --watch
   ```

4. When every case passes, finish the attempt and say how it went:

   ```bash
   cstudy done --rating ok              # easy, ok or hard; --gave-up if it never passed
   ```

`cstudy done` schedules the next review, and `cstudy next` brings the problem back when it is due. [Work on a problem](practice.md) covers hints, solutions and the rest of the loop.

## Practise in your browser

`cstudy serve` opens a page on your own computer with the same loop: the problem list, the statement, an editor over your files, test runs, hints, solutions, mock interviews, your progress and these docs. It works on the same workspace as the terminal and your IDE, so you can switch at any time.

```bash
cstudy serve --open                    # Ctrl-C stops it
```

[Practise in your browser](web-ui.md) covers the page.

## Learn before you practise

Concept guides teach an idea before you practise it, and learning paths put guides and problems in order, from a topic's first idea to an expert's:

```bash
cstudy learn                           # the guides and paths, with what you have read
cstudy learn --path getting-started    # a path's steps and the next one
```

[Guides and learning paths](guides.md) has more.

## The main commands

| Command | Does |
|---------|------|
| `cstudy init [PATH]` | Creates a workspace |
| `cstudy doctor [--fix]` | Checks the toolchains and the workspace; `--fix` sets up the projects |
| `cstudy next` | Picks what to practise: an attempt you have open, a due review, or a new problem |
| `cstudy start <slug> [--lang L]` | Writes the stub, renders the statement, opens your editor, begins an attempt |
| `cstudy test [--watch]` | Runs your code against the cases |
| `cstudy hint` | Shows the next hint |
| `cstudy solution <slug>` | Shows the reference solutions with their explanation |
| `cstudy done --rating easy\|ok\|hard` | Finishes the attempt and schedules the review |
| `cstudy bench` | Measures how your solution grows with the input, beside the reference approaches |
| `cstudy list`, `cstudy show <slug>` | Browses the catalog; prints a statement |
| `cstudy learn [<guide>] [--path P]` | Reads the concept guides and follows a learning path |
| `cstudy set create <name>` | Makes a named list of problems to study from ([plan your practice](planning.md)) |
| `cstudy stats`, `cstudy mock` | Shows your progress; runs a timed mock interview |
| `cstudy serve [--open]` | Serves the practice page on your computer |
| `cstudy docs [<topic>]` | Reads these pages in the terminal |
| `cstudy about` | Shows the version, the license, the links and the credits |

Every command takes `--help`. `cstudy docs` lists every topic, and `cstudy docs <topic>` prints one, such as `cstudy docs practice`.
