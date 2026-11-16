---
title: Command reference
summary: Every cstudy command with its flags, by group, then the global flags, the exit codes, the environment variables, the configuration keys and how the JDK is selected.
section: Settings and help
order: 125
---

# Command reference

Every `cstudy` command, with the flags it takes and what it does. `cstudy <command> --help` prints the same for one command, with each flag's default.

In the tables, words in angle brackets are what you type. `<slug>` is a problem's slug, such as `two-sum`, or its solution file; in brackets, `[<slug>]`, you can leave it out, and the command acts on the attempt you used last. The values that flags take:

| Placeholder | Values |
|-------------|--------|
| `<language>` | `python`, `typescript`, `java`, `kotlin`, `go`, `rust` |
| `<track>` | `dsa`, `practical`, `lld`, `concurrency`, `debugging`, `system-design`, `code-review`, `behavioral` |
| `<kind>` | `function`, `design`, `progressive`, `concurrent`, `project`, `system-design`, `code-review` |
| `<difficulty>` | `easy`, `medium`, `hard` |
| `<scope>` | `function`, `project`, `system` |
| `<domain>`, `<role>` | A label value ([labels](problem-kinds.md#labels)) |

## Global flags

Global flags come before the command:

```bash
cstudy --workspace ~/cstudy-workspace next
cstudy --no-color list --track dsa
```

| Flag | Does |
|------|------|
| `--workspace <path>` | Uses this workspace, instead of `CSTUDY_WORKSPACE`, the nearest workspace above the current folder, or the current folder ([how cstudy finds it](workspace.md#how-cstudy-finds-it)) |
| `--content <path>` | Reads the problems and runners from this checkout of the `cstudy` source, instead of `CSTUDY_CONTENT` or the content `cstudy` ships with |
| `--no-color` | Plain output. `NO_COLOR`, or output to a pipe or a file, does the same |
| `--version` | Prints the version and exits |
| `--help` | Lists the commands. After a command, it describes that command |

`--json` and `--events` belong to the commands that have them, so they come after the command, as in `cstudy stats --json`.

## Practice

| Command | Flags | Does |
|---------|-------|------|
| `cstudy start <slug>` | `--lang <language>`, `--timer <duration>`, `--fresh`, `--no-open`, `--restore <path>`, `--yes` | Begins an attempt, or resumes the open one: writes the stub, renders the statement and opens both in your editor. `--timer` takes `25m` or `1h`; `--fresh` moves your earlier file to `.archive/`; `--restore` writes one starter or generated test file of a project back as `cstudy` provides it; `--yes` lets a service project download what it needs without asking ([work on a problem](practice.md#start)) |
| `cstudy test [<slug>]` | `--lang <language>`, `--watch`, `--case <id>`, `--all`, `--typecheck`, `--time-limit=<value>`, `--no-time-limit`, `--level <n>`, `--perf`, `--stress <n>`, `--seed <seed>`, `--json`, `--events`, `--debug`, `--debug-port <port>`, `--debug-connect` | Runs your code against the cases. `--watch` runs again on every save; `--case` runs only that case; `--all` prints the passing hidden cases too; `--typecheck` also type-checks TypeScript; `--time-limit` turns time limits on, alone or with a factor (`=5x`) or a duration (`=1500ms`), and `--no-time-limit` turns them off; `--level` runs levels 1 to n; `--perf` runs a short benchmark after a full pass; `--stress` sets the runs of each stress case, or the generated inputs checked against the oracle; `--seed` sets the base seed. `--debug` and its flags are in [debug a run](ide-and-debugging.md#debug-a-run) |
| `cstudy submit [<slug>]` | `--level <n>`, `--json`, `--events` | Grades a project problem, every open level or levels 1 to n, and opens the next level when one passes ([project problems](levels.md#project-problems)) |
| `cstudy dev [<slug>]` | `--scenario <mock>=<scenario>`, `--events`, `--no-run`, `--debug`, `--reset-data`, `--exec`, `--network` | Runs a service project's stack in the foreground until `Ctrl+C`. `--scenario` starts a mock server on one of its scenarios, and repeats; `--no-run` keeps the app container idle for your IDE; `--debug` runs your app under its debugger; `--reset-data` removes the stack's data first; `--exec` runs the command after `--` in a one-off app container, and `--network` gives that command the internet and no stack ([the dev stack](service-projects.md#the-dev-stack)) |
| `cstudy hint [<slug>]` | - | Shows the next hint. Any hint caps the attempt's grade at `ok` |
| `cstudy solution <slug>` | `--lang <language>`, `--approach <id>`, `--all`, `--explanation-only`, `--yes`, `--broken` | Shows the reference code with its explanation. `--approach` shows one approach, `--all` every one; `--explanation-only` leaves the code out; `--yes` shows it without asking while your attempt has not passed; `--broken` shows a concurrency problem's broken reference, and `--broken=<id>` a given one ([concurrency problems](problem-kinds.md#concurrency-problems)) |
| `cstudy bench [<slug>]` | `--lang <language>`, `--sizes <list>`, `--reps <n>`, `--refs-only`, `--no-memory` | Measures how your solution's time grows with the input, beside the reference approaches, and gives a verdict: `optimal`, `near-optimal` or `suboptimal`. `--sizes` takes comma-separated sizes; `--reps` sets the timed repetitions per size; `--refs-only` measures only the references; `--no-memory` skips the memory measurements |
| `cstudy status [<slug>]` | `--json` | Shows where the attempt stands: its time, hints and latest run |
| `cstudy done [<slug>]` | `--rating <rating>`, `--gave-up`, `--notes <text>` | Finishes the attempt and schedules its review: `--rating` is `easy`, `ok` or `hard`, after a pass; `--gave-up` finishes without one; `--notes` keeps a note on the attempt ([finish](practice.md#finish)) |
| `cstudy abort [<slug>]` | `--yes` | Ends the attempt as abandoned, after a question. Your files stay, and your progress does not change |

## Plan and track

| Command | Flags | Does |
|---------|-------|------|
| `cstudy next` | `--set <name>`, `--track <track>`, `--pattern <pattern>`, `--difficulty <difficulty>`, `--lang <language>`, `--domain <domain>`, `--role <role>`, `--scope <scope>`, `--new`, `--review`, `--start`, `--json` | Picks what to practice: an open attempt, a due review, or a new problem. `--track` repeats; `--new` skips reviews, `--review` skips new problems; `--start` starts the pick ([what to do next](planning.md#what-to-do-next)) |
| `cstudy list` | `--set <name>`, `--track <track>`, `--pattern <pattern>`, `--difficulty <difficulty>`, `--status <status>`, `--content <status>`, `--lang <language>`, `--kind <kind>`, `--domain <domain>`, `--role <role>`, `--scope <scope>`, `--search <text>`, `--needs <what>`, `--checked-by <how>`, `--json` | Lists problems. `--status` is `new`, `in_progress`, `attempted`, `passed`, `due` or `mastered`; `--content` is `draft` or `ready`; `--lang` keeps problems with a reference in that language; `--search` matches the slug or the title; `--needs none` keeps problems that need only the language's toolchain, and `--needs docker` those that need Docker; `--checked-by` is `tests` or `rubric` |
| `cstudy show <slug>` | `--level <n>` | Prints the statement, never the hints. `--level` shows levels 1 to n of the open ones |
| `cstudy history <slug>` | `--json` | Shows every attempt, run and review of a problem, and when it comes back |
| `cstudy stats` | `--by <group>`, `--since <date>`, `--json` | Summarizes your progress, by `pattern`, `track`, `lang` or `difficulty`; `--since` takes a date, `2026-10-01` ([your progress](planning.md#your-progress)) |
| `cstudy mock` | `--minutes <n>`, `--count <n>`, `--track <track>`, `--lang <language>` | Runs a timed mock interview: a few problems under one timer, with hints and solutions locked until it ends ([mock interviews](planning.md#mock-interviews)) |
| `cstudy set list` | `--json` | Lists your sets, each with how many of its problems you passed ([problem sets](planning.md#problem-sets)) |
| `cstudy set show <name>` | `--json` | Shows a set's problems, in its order |
| `cstudy set create <name>` | `--description <text>` | Creates an empty set, named by a slug such as `backend-loop` |
| `cstudy set add <name> <slug>...` | `--level <n>` | Adds problems to the end of a set. `--level` counts a progressive or project problem as done once a pass reaches that level |
| `cstudy set remove <name> <slug>...` | - | Takes problems out of a set |
| `cstudy set move <name> <slug> <position>` | - | Moves a problem within a set, to a position counted from 1 |
| `cstudy set rename <name> <new-name>` | - | Renames a set, keeping its problems |
| `cstudy set delete <name>` | `--yes` | Deletes a set, after a question. Your progress stays |

## Learn

| Command | Flags | Does |
|---------|-------|------|
| `cstudy learn [<guide>]` | `--path <path>`, `--done`, `--search <text>`, `--level <level>`, `--status <status>`, `--open`, `--json`, `--lang <language>` | Lists the concept guides and learning paths, or prints a guide. `--path` shows a path's steps; `--done` marks the guide read; `--search` matches every word; `--level` is `intro`, `core` or `advanced`; `--status` is `read` or `not_read`; `--lang` picks the language of a guide's examples; `--open` opens it in the web UI ([guides](guides.md#in-the-terminal)) |
| `cstudy docs [<topic>]` | `--open`, `--json` | Lists these pages, or prints one, such as `cstudy docs commands`. `--open` opens it in the web UI |

## Workspace and setup

| Command | Flags | Does |
|---------|-------|------|
| `cstudy init [<path>]` | `--git`, `--ide <ide>`, `--no-ide`, `--force` | Creates a workspace. `--git` runs `git init` there; `--ide` is `vscode` or `idea`, and repeats; `--no-ide` writes no IDE files; `--force` allows a workspace inside a checkout of the `cstudy` source ([create one](workspace.md#create-one)) |
| `cstudy doctor` | `--fix`, `--json`, `--accept-license <server>` | Checks the toolchains, your configuration and the workspace. `--fix` sets up the workspace's projects and repairs what it can; `--accept-license kotlin-lsp`, with `--fix`, accepts that language server's license so that it downloads ([check your setup](doctor.md)) |
| `cstudy ide [<ide>]` | `--force` | Writes or refreshes the IDE project files and the IntelliJ IDEA launcher: `vscode`, `idea`, or `all`, the default. `--force` also overwrites the files you edited ([your edits and cstudy ide](ide-and-debugging.md#your-edits-and-cstudy-ide)) |
| `cstudy lang list` | - | Shows the workspace's languages and their folders |
| `cstudy lang add <language>...` | - | Adds languages to the workspace: writes the folder files each one lacks, never overwriting one, and refreshes the IDE files `cstudy` wrote. `cstudy doctor --fix` then installs the toolchain files |
| `cstudy lang remove <language>...` | `--delete-folder`, `--yes` | Takes languages out of the workspace. Their folders, your practice files and your progress stay; a removed language stops being checked, generated for and offered. `--delete-folder` also deletes each language's folder, after a preview and a question; `--yes` does not ask. It refuses while an attempt in a removed language is in progress, and the folders cannot be recovered. A workspace needs at least one language |
| `cstudy config path` | - | Prints the path of your `config.toml` |
| `cstudy config edit` | - | Opens your `config.toml` in `$VISUAL` or `$EDITOR`, and creates it when it is missing ([your configuration](settings.md#your-configuration)) |
| `cstudy about` | `--credits`, `--licenses` | Shows the version, the license, the links and the credits. `--credits` lists the software `cstudy` uses; `--licenses` prints the full license texts |

## Content

| Command | Flags | Does |
|---------|-------|------|
| `cstudy new <slug>` | `--from-template <template>`, `--track <track>`, `--title <title>`, `--difficulty <difficulty>`, `--pattern <pattern>`, `--virtual-clock`, `--stress` | Writes a draft problem of your own in the workspace's `problems/` ([create one](own-problems.md#create-one)) |
| `cstudy verify [<slug>...]` | `--static`, `--oracle`, `--oracle-cases <n>`, `--ladder`, `--require-ready`, `--changed`, `--track <track>`, `--lang <language>`, `--skip-lang <language>`, `--conformance`, `--jobs <n>`, `--stress <n>` | Checks problems: every one without slugs. `--static` runs the file checks only; `--oracle` checks every approach against the oracle, `--oracle-cases` sets how many inputs; `--ladder` measures the references; `--require-ready` fails a problem that is not `ready`; `--changed` checks the problems whose files changed from git's `main`; `--skip-lang` leaves a language out, and a language whose toolchain is missing is skipped and named, not fatal ([check it](own-problems.md#check-it)); `--conformance` checks the runners; `--jobs` sets how many language runners work at once; `--stress` sets the runs of each stress case ([check it](own-problems.md#check-it)) |

## Progress data

| Command | Flags | Does |
|---------|-------|------|
| `cstudy export` | `--out <path>` | Writes your progress as JSON, to `progress-export.json` in the workspace unless `--out` names a file ([back up and restore](settings.md#back-up-and-restore-your-progress)) |
| `cstudy import [<path>]` | - | Restores an export, `progress-export.json` unless you name one, into an empty `progress.db` |
| `cstudy reset` | `--files`, `--archive`, `--yes` | Deletes your progress and state, after a preview and your typing `reset`. `--files` also deletes your practice files, project folders and notes; `--archive` also deletes `.archive/`; `--yes` does not ask. This cannot be undone ([start over](settings.md#start-over)) |

## Web UI

| Command | Flags | Does |
|---------|-------|------|
| `cstudy serve` | `--port <port>`, `--open` | Serves the web UI on 127.0.0.1 until `Ctrl+C`, on a free port unless `--port` names one. `--open` opens the page in your default browser ([start the server](web-ui.md#start-the-server)) |

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
| 129 | It was hung up (SIGHUP) during a `cstudy test --debug` run |
| 130 | You stopped it with `Ctrl+C` |
| 143 | It was stopped with SIGTERM: during a `cstudy test` or `cstudy submit` run with `--events`, during a `cstudy test --debug` run, or while `cstudy serve` runs |

[Troubleshooting](troubleshooting.md#errors-by-command) lists the messages behind them, command by command.

## Environment variables

`cstudy` reads these variables. A flag, where one exists, wins over its variable.

| Variable | `cstudy` reads it for |
|----------|-----------------------|
| `CSTUDY_WORKSPACE` | The workspace, when you give no `--workspace` ([how cstudy finds it](workspace.md#how-cstudy-finds-it)). `cstudy init` without a path creates the workspace there |
| `CSTUDY_CONTENT` | A checkout of the `cstudy` source to read the problems and runners from, when you give no `--content` |
| `CSTUDY_CONFIG` | Another `config.toml` than the usual one ([your configuration](settings.md#your-configuration)) |
| `XDG_CONFIG_HOME` | The folder that holds `coding-study/config.toml`; `~/.config` when it is not set |
| `XDG_CACHE_HOME` | The folder of the catalog cache that `cstudy list` and `cstudy show` keep outside a workspace, `coding-study/catalog`; `~/.cache` when it is not set |
| `NO_COLOR` | Plain output, as `--no-color` gives |
| `VISUAL`, `EDITOR` | The editor that `cstudy start` and `cstudy mock` open while `open_on_start` is on, and that `cstudy config edit` opens. `VISUAL` comes first; with neither set, the command says to set one |
| `MANPAGER`, `PAGER` | The pager that `cstudy solution` shows its text in on a terminal, in that order; with neither set, the system's pager, such as `less` |
| `JAVA_HOME` | The JDK that runs Java and Kotlin ([the selected JDK](#the-selected-jdk)) |
| `PATH` | The toolchains, the first `java` when `JAVA_HOME` is not set, and the copies of `cstudy` that the `installs` row of `cstudy doctor` lists |
| `GRADLE_USER_HOME` | Gradle's home, `~/.gradle` when it is not set, where `cstudy` looks for a Gradle daemon that already runs, to decide whether to say that a build starts one |
| `GOBIN`, `GOPATH` | Delve, for a Go debug run, when it is not on `PATH`: in `GOBIN`, then in `bin` of the first `GOPATH` entry, `~/go/bin` when neither is set |
| `LLDB_DEBUGSERVER_PATH` | On macOS, the `debugserver` of a Rust debug run, tried before `PATH` and the developer directory |
| `DEVELOPER_DIR` | On macOS, the Xcode or Command Line Tools to take `debugserver` from, instead of the one `xcode-select -p` names |
| `XDG_RUNTIME_DIR` | On Linux, where rootless Docker keeps its socket, which tells rootless Docker from a system engine ([Docker](toolchains.md#docker)) |
| `DOCKER_HOST`, `DOCKER_CONTEXT`, `DOCKER_CONFIG`, `DOCKER_CERT_PATH`, `DOCKER_TLS_VERIFY` | Which Docker engine the Docker client talks to, for service projects. Only the Docker client gets them, never a container |
| `XDG_DATA_HOME`, `UV_TOOL_DIR`, `PIPX_HOME` | Where uv and pipx keep the tools they install, so that `cstudy doctor` can say how each copy of `cstudy` on your `PATH` was installed |
| `CSTUDY_EXECUTABLE` | The `cstudy` that the IntelliJ IDEA launcher runs, before it looks on `PATH` ([IntelliJ IDEA](ide-and-debugging.md#intellij-idea)) |

The code that `cstudy` runs, with its builds, installs and language servers, starts with only part of your environment ([your environment](toolchains.md#your-environment)). `cstudy` also fixes some settings of its own Go and Rust builds, whatever your shell says ([Go](toolchains.md#go), [Rust](toolchains.md#rust)).

## Configuration keys

Every key of `config.toml`, in the order of the file. A dotted key is a key of a table: `schedule.max_interval_days` is `max_interval_days` under `[schedule]`. A key you leave out has its default. [Your configuration](settings.md#your-configuration) says where the file is, how to edit it and when a change applies.

| Key | Default | Does |
|-----|---------|------|
| `default_lang` | `"python"` | The language of `cstudy start`, `cstudy next` and `cstudy mock` when you give no `--lang` |
| `open_on_start` | `true` | Opens `$VISUAL` or `$EDITOR` on `cstudy start` |
| `progress_db` | `"progress.db"` | The progress database, relative to the workspace root. Changing it moves no data ([change progress_db](settings.md#change-progress_db)) |
| `next.tracks` | `["dsa"]` | The tracks `cstudy next` and `cstudy mock` pick from when you give no `--track` |
| `time_limit.enabled` | `false` | Applies time limits to every run, as `cstudy test --time-limit` does to one |
| `time_limit.value` | not set | The limit: a factor of the reference, such as `"5x"`, or a duration, such as `"1500ms"`. Not set, the problem's suggested limit applies, else `5x` |
| `time_limit.floor_ms` | `100` | A limit by factor never goes below this many milliseconds. A duration is used as it is |
| `hang_guard.ms` | not set | Stops a case that runs this many milliseconds. Not set, the case's or the problem's own value applies, then `10000` |
| `bench.reps` | `7` | Timed repetitions per size in `cstudy bench` |
| `bench.memory` | `true` | Measures memory as well as time in `cstudy bench` |
| `schedule.penalize_suboptimal` | `true` | A `suboptimal` benchmark verdict caps the grade at `hard` |
| `schedule.max_interval_days` | `180` | No review is scheduled further away than this |
| `schedule.again_interval_days` | `1` | Days to the next review after an `again` |
| `schedule.hard_first_interval_days` | `2` | Days after a first review graded `hard` |
| `schedule.ok_first_interval_days` | `3` | Days after a first review graded `ok` |
| `schedule.ok_second_interval_days` | `7` | Days after a second review graded `ok` |
| `schedule.easy_first_interval_days` | `5` | Days after a first review graded `easy` |
| `schedule.easy_second_interval_days` | `12` | Days after a second review graded `easy` |
| `schedule.mastered_interval_days` | `21` | A problem counts as mastered from this review interval on, with a grade of `ok` or `easy` |
| `done.auto_commit` | `false` | Reserved: it does nothing yet |
| `study_guides.root` | not set | The folder of your study guides, an absolute path or one that starts with `~/` ([point to your study guides](settings.md#point-to-your-study-guides)) |

## The selected JDK

Java and Kotlin run on one JDK: the one your shell selects. That is the JDK that `JAVA_HOME` names, or, when `JAVA_HOME` is not set, the JDK of the first `java` on your `PATH`, as the Gradle wrapper chooses. A `JAVA_HOME` that holds no JDK selects nothing: `cstudy` does not look on your `PATH` then, and never searches for other JDKs.

| Rule | Detail |
|------|--------|
| Range | `cstudy` supports JDK 21 to 26. A problem can need a newer JDK than 21, and its statement says so |
| Outside the range | `cstudy start`, `cstudy test`, `cstudy submit` and `cstudy bench` refuse a Java or Kotlin version of a problem before they write or build anything, and exit 4 with the fix. Commands that run no code, and the other languages, are unaffected |
| `cstudy list` | Lists every problem, and marks `java!` and `kt!` in the references column where the JDK cannot run a problem, with one line under the table that says why |
| `cstudy verify` | Skips the Java and Kotlin of a problem whose range does not hold the JDK, with a `skipped` line that names the range and the JDK. `--require-ready` counts a skip as not passed |
| `cstudy next`, `cstudy mock` | Never pick a problem that the JDK cannot run in the language you practice. When that leaves nothing, they say so |
| `cstudy show` | Names the problem's own JDK range in its statement, when it has one |
| `cstudy doctor` | Shows the JDK and where it came from: `java 25.0.5 (JAVA_HOME)` |
| Everything Java and Kotlin | Gradle, the compilers and the runner all use the selected JDK, so switching it, with `JAVA_HOME` or a version manager, switches every command |

[JDK](toolchains.md#jdk) covers installing one and switching between several.
