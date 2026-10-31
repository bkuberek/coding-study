# coding-study

coding-study is a local, IDE-first practice system for senior and staff software engineering interviews. You solve original problems in your own editor in Python, TypeScript, Java, Kotlin, Go, or Rust, and the `cstudy` command line tests your code, checks whether it is optimal, shows reference solutions, and schedules reviews with spaced repetition. Everything runs on your machine; there is no account and no service.

- **Your editor, real toolchains.** Each language is an ordinary project (uv, pnpm, Gradle) that your editor and its language server open directly.
- **More than algorithms.** Data structures and algorithms, multi-level practical problems, low-level design, concurrency, debugging, system design, and code review.
- **Optimality, not only correctness.** `cstudy bench` measures how your solution grows with input size and compares it with the reference approaches.
- **Spaced repetition.** `cstudy next` brings back what is due and picks new problems from your weakest pattern.

## Install

Install `cstudy` once; the problems, tracks and runners ship with it. With Homebrew:

```bash
brew install bkuberek/tap/cstudy
cstudy --version
```

Homebrew also installs the Python that `cstudy` runs on. Upgrade with `brew upgrade cstudy`. Homebrew 7 asks you to trust a third-party tap before commands such as `brew info cstudy` read it: run `brew trust bkuberek/tap` once. Each release reaches the tap automatically ([versioning](docs/specs/versioning.md#homebrew-tap)).

Or with uv or pipx, from the repository:

```bash
uv tool install git+https://github.com/bkuberek/coding-study
# or: pipx install git+https://github.com/bkuberek/coding-study
```

Upgrade with `uv tool upgrade coding-study` (or `pipx upgrade coding-study`). Keep one of these installs: when several exist, the `cstudy` whose directory comes first on `PATH` runs (`which -a cstudy` lists them).

## Install the language toolchains

`cstudy` runs your solutions with the real toolchain of each language, which you install yourself. uv and Python are required; Node.js, the JDK, Go and Rust are needed only for the languages that use them. Problems have reference solutions in all six languages, except where a language cannot express one or a bug exists in some languages only ([catalog](docs/specs/catalog.md)), so you can practice in any of them. The recommended install on macOS:

| Tool | Version | Needed for | Install on macOS |
|------|---------|------------|------------------|
| [uv](https://docs.astral.sh/uv/) | 0.10 or newer | Required: manages Python and the Python practice project | `brew install uv` |
| Python | 3.13 | Required | `uv python install 3.13` |
| [Node.js](https://nodejs.org/) | 24 or newer | Optional: TypeScript | `brew install fnm`, then `fnm install 24` |
| [pnpm](https://pnpm.io/) | 9 or newer | Optional: TypeScript | `corepack enable pnpm` |
| JDK | 21 exactly | Optional: Java and Kotlin (the workspace's Gradle wrapper downloads Gradle and the Kotlin compiler) | [SDKMAN!](https://sdkman.io): `sdk install java` with a Temurin 21 identifier from `sdk list java` |
| [Go](https://go.dev/) | 1.24 or newer | Optional: Go (`--lang go`) | `brew install go` |
| [Rust](https://www.rust-lang.org/) | 1.80 or newer | Optional: Rust (`--lang rust`) | `brew install rustup`, then `rustup-init` |
| git | any | Optional: versioning your workspace | `xcode-select --install` |

[Install the language toolchains](docs/guides/toolchains.md) has the full steps, Linux, and the check for each. Then run `cstudy doctor`: it checks each tool and prints a fix for anything missing. In a workspace, `cstudy doctor --fix` also sets up the practice projects.

## Quickstart

You practice in a **workspace**: a directory of your own for your solutions, notes and progress, separate from this repository.

1. Create the workspace and set up its toolchains:

   ```bash
   cstudy init ~/cstudy-workspace --git   # --git runs git init; cstudy never commits
   cd ~/cstudy-workspace
   cstudy doctor --fix                # uv sync, pnpm install, Gradle warm-up, runner checks
   ```

2. Pick a problem and start it. `cstudy start` writes a stub and the statement, then opens both in `$VISUAL` or `$EDITOR`:

   ```bash
   cstudy next                        # suggests a problem and prints the command to start it
   cstudy start two-sum               # add --lang typescript, java, or kotlin; default: python
   ```

3. Solve it in your IDE. Open the language's project in the workspace as the editor root (`python/`, `typescript/`, or `jvm/`) for diagnostics without extra configuration.
4. Test on every save, then finish the attempt with how it went:

   ```bash
   cstudy test --watch
   cstudy done --rating ok            # easy, ok, or hard; --gave-up if it never passed
   ```

`cstudy done` schedules the next review, and `cstudy next` brings the problem back when it is due. A missing Node.js, pnpm or JDK shows as `FAIL` in `cstudy doctor` and a missing Go or Rust as `WARN`; the other languages still work.

## Your workspace is your repository

The workspace holds your practice files, notes, previous attempts (`.archive/`) and your own problems. Version it in a git repository of your own, separately from this one: its `.gitignore` already excludes per-machine state such as `progress.db` and build output. Back up progress with `cstudy export`, which writes a JSON file you can commit. On another machine, clone your workspace and run `cstudy doctor --fix`.

Run `cstudy` anywhere inside the workspace, or point at it with `cstudy --workspace PATH` or `CSTUDY_WORKSPACE=PATH`. Details: [installation and workspaces](docs/specs/installation-and-workspaces.md).

## Main commands

| Command | Does |
|---------|------|
| `cstudy init [PATH]` | Creates a workspace |
| `cstudy doctor [--fix]` | Checks the toolchains and the workspace; `--fix` installs the project dependencies |
| `cstudy next [--track T]` | Picks a due review, or a new problem from your weakest pattern |
| `cstudy start <slug> [--lang L]` | Writes the stub, renders the statement, opens your editor, begins an attempt |
| `cstudy test [--watch]` | Runs your code against the cases |
| `cstudy hint` | Reveals the next hint |
| `cstudy solution [<slug>]` | Shows the reference solutions with their explanation |
| `cstudy done --rating easy\|ok\|hard` | Finishes the attempt and schedules the review |
| `cstudy bench` | Measures how your solution scales and compares it with the reference approaches |
| `cstudy list`, `cstudy show <slug>` | Browses the catalog; prints a statement |
| `cstudy stats`, `cstudy mock` | Shows your progress; runs a timed mock interview |
| `cstudy new <slug>`, `cstudy verify <slug>` | Scaffolds a problem of your own; checks it |

Every command and flag: [CLI reference](docs/specs/cli.md). Configuration, such as the default language, lives in `~/.config/coding-study/config.toml` ([configuration](docs/specs/cli.md#configuration)).

## Content catalog

All problem statements, tests and solutions are original ([ADR 0004](docs/decisions/0004-original-problem-wording.md)); LeetCode references only link to the well-known problem a statement is modeled on.

| Track | Items | Graded by | Format |
|-------|------:|-----------|--------|
| `dsa` | 196 | Tests, in all 6 languages | Functions and data-structure designs across 23 patterns |
| `practical` | 23 | Tests, level by level where a problem has levels | One class whose API grows over 4 levels, or a business task with money and dates |
| `lld` | 8 | Tests, then a design rubric | Object-oriented design |
| `concurrency` | 6 | Stress tests against invariants | Thread-safe classes, per-language models |
| `debugging` | 16 | Tests | Buggy code to fix, including Go- and Rust-only bugs |
| `system-design` | 10 | Self-graded with a rubric | Prompt, notes template, reference design |
| `code-review` | 6 | Self-graded with a rubric | A change to review |
| `behavioral` | none | Not tracked | Guidance for your own story bank |

Track details: [content](docs/specs/content.md). Every problem: [catalog](docs/specs/catalog.md).

## Write your own problems

`cstudy new my-problem` in your workspace scaffolds a problem in the workspace's `problems/` directory, numbered from 5001, and it joins the catalog for every command. Start from a template (`--from-template array|tree|design|progressive|concurrent`), write the statement, tests, and reference solutions, then check it:

```bash
cstudy verify my-problem --oracle --require-ready
```

The [authoring guide](docs/specs/authoring.md) covers the workflow and the ready criteria, and the [problem format](docs/specs/problem-format.md) defines every file.

## Documentation

| Read | For |
|------|-----|
| [Documentation index](docs/README.md) | The PRD, architecture, specs, and decision records |
| [CLI reference](docs/specs/cli.md) | Every command, flag, output, and exit code |
| [Contributing](CONTRIBUTING.md) | Development setup, checks, authoring content, and commit conventions |
| [Versioning](docs/specs/versioning.md) and [changelog](CHANGELOG.md) | How releases are numbered from Conventional Commits |

## License

[MIT](LICENSE), covering both the code and the original problem content.
