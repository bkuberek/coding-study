---
title: Troubleshooting
summary: What to do when a command fails, a toolchain is missing, the web UI loses its server, a language server stops, or the AI preview refuses a request.
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
| 4 | Something on your machine is missing: a toolchain, a JDK in range, a runner that did not start; or an AI provider failed ([the AI preview](ai.md#when-a-request-fails)) |
| 5 | A content file is wrong: a problem, a guide or a page that fails its checks |
| 70 | A bug in `cstudy`. Please report it |
| 129 | It was hung up (SIGHUP) during a `cstudy test --debug` run |
| 130 | You stopped it with `Ctrl+C` |
| 143 | It was stopped with SIGTERM: during a `cstudy test` or `cstudy submit` run with `--events`, during a `cstudy test --debug` run, or while `cstudy serve` runs |

## Commands

| You see | Do |
|---------|----|
| `no coding-study workspace at …: run cstudy init` | Run the command inside your workspace, pass `--workspace PATH`, or set `CSTUDY_WORKSPACE`. Create one with `cstudy init` ([your workspace](workspace.md)) |
| `unknown problem "…"` | `cstudy list --search <word>` finds the slug |
| `no attempt in progress; start one with cstudy start <slug>` | Start one, or name the problem: `cstudy test two-sum` |
| A `FAIL` row in `cstudy doctor` | Run the `fix:` it prints. For a toolchain, follow [install the language toolchains](toolchains.md) |
| `cstudy doctor` warns on `installs` | Several copies of `cstudy` are on your `PATH`, and only the first runs. Keep one: the row's `fix:` names the command that removes each other copy. `which -a cstudy` lists them |
| `java 27 (not supported yet …)` or a JDK that is too old | `cstudy` runs Java and Kotlin on JDK 21 to 26. Select one with `JAVA_HOME`, or install JDK 25 ([JDK](toolchains.md#jdk)) |
| `go was not found on PATH`, `cargo was not found on PATH` | Go and Rust are optional; install them only for `--lang go` or `--lang rust`, or once your workspace lists Go or Rust, which makes them required ([Go](toolchains.md#go), [Rust](toolchains.md#rust)) |
| `rust is not one of this workspace's languages (python, go): cstudy lang add rust` | A new attempt starts only in one of the workspace's languages. Add the language with the command it names, then run `cstudy doctor --fix`, or start the problem in a language the workspace lists ([choose its languages](workspace.md#choose-its-languages)) |
| A list shows fewer problems or guides than you expect, and ends with `filtered by your profile:` | Your learner profile hides the rest. `--widen all` shows them for one run; the **profile** section of Settings, `cstudy config edit` and `cstudy lang` change the profile ([your learner profile](settings.md#your-learner-profile)) |
| `nothing to pick in your profile (…); widen with cstudy next --widen all`, or the same from `cstudy mock` | Nothing your profile keeps is left to pick. Run the command it names, choose other tracks with `--track`, or widen your profile |
| The first Java or Kotlin run is slow | Gradle starts its daemon and compiles once; later runs are quicker. `cstudy doctor --fix` warms it up ahead of time |
| progress.db uses schema `<n>`, newer than the `<m>` this cstudy reads: upgrade cstudy | A newer `cstudy` wrote it, and this one cannot read it. Upgrade `cstudy` ([older workspaces](upgrading.md#older-workspaces)) |
| `cstudy hint is locked during the mock interview` | Hints and solutions unlock when the mock's timer ends or every problem is done ([mock interviews](planning.md#mock-interviews)) |
| A service project says Docker is missing or not running | Install or start Docker; `cstudy` starts a stopped engine itself when it can, and says what to run when it cannot ([Docker](toolchains.md#docker)) |
| Output with colors you do not want | Pass `--no-color`, or set `NO_COLOR`. Output to a pipe or a file has no colors |

## Errors by command

Each message below follows `error: ` in your terminal, word for word. Words in angle brackets stand for what the message names: `<slug>` the problem, `<path>` the file you gave, `<range>` the JDKs a problem runs on (such as JDK 21 to 26), and `<source>` where your JDK came from, `JAVA_HOME` or `PATH`.

| Command | You see | It means | Do |
|---------|---------|----------|----|
| Any command in a workspace | the workspace at `<path>` uses schema `<n>` (created with cstudy `<version>`); this cstudy reads schema `<m>`: upgrade cstudy | A newer `cstudy` wrote the workspace's marker, and this one cannot read it. Exit 3 | Upgrade `cstudy` ([older workspaces](upgrading.md#older-workspaces)) |
| Any command that opens your progress | `cannot back up progress.db before migrating it: <reason>; nothing changed` | The copy that comes before a migration failed, so `progress.db` stays as it was. Exit 4 | Fix the reason, such as a full disk, then run the command again |
| Any command that opens your progress | `migrating progress.db from schema <n> failed at schema <m>: <reason>; restored it from .cs/backups/<file>` | A migration step failed, and `cstudy` put the copy back. Exit 4 | Run the command again. If it fails the same way, report it with the message |
| Any command that opens your progress | `migrating progress.db from schema <n> failed at schema <m>: <reason>, and restoring it failed: <reason>; copy .cs/backups/<file> over progress.db` | The migration failed, and putting the copy back failed too. Exit 4 | Copy that file over `progress.db` yourself, then run the command again |
| A command given a file, such as `cstudy test <file>` | `open a solution file in the editor first (got a directory: <path>)` | Your IDE passed a folder, because no file had the focus when you ran its task. Exit 3 | Click into your solution file, then run the task again |
| A command given a file | `not a solution file in this workspace: <path>` | The path is outside the workspace, or is not a file that `cstudy start` writes. Exit 3 | Name the problem's slug, or a solution file of the workspace |
| A command given a file | `not a solution file in this workspace: <path> (<slug> is not a project problem)` | The file is under `projects/<slug>/`, but that problem is not a project problem. Exit 3 | Name the problem's slug instead |
| A command given a file | `no problem for <path>: none is named <name>` | The file's name matches no problem. Exit 3 | Check the file's name, or name the problem's slug |
| A command given a file | `<path> is a <language> file but --lang <language> was given` | `--lang` says another language than the file. Exit 3 | Leave `--lang` out: the file says the language |
| `cstudy start` | `<slug> is not available in <language>; use <languages>` | The problem has no version in that language. Exit 3 | Pass one of the languages it lists with `--lang` |
| `cstudy start` | `<slug> is not autograded; --lang applies to autograded problems` | A `system-design` or `code-review` problem has no language: you answer it in notes. Exit 3 | Leave `--lang` out |
| `cstudy start` | `cstudy start <slug> would download what is listed: pass --yes to go on` | A service project needs downloads, and there is no terminal to ask you. Exit 3 | Read the list it printed, then run it again with `--yes` |
| `cstudy start`, `cstudy test`, `cstudy submit`, `cstudy bench` | `<slug>` runs its `<language>` version on `<range>`; `<source>` selects JDK `<n>`, which cstudy does not support yet | Your JDK is newer than any `cstudy` supports. Exit 4, with a `fix:` line | Select a JDK in the range with `JAVA_HOME`, as the `fix:` says ([JDK](toolchains.md#jdk)) |
| `cstudy start`, `cstudy test`, `cstudy submit`, `cstudy bench` | `<slug> runs its <language> version on <range>; <source> selects JDK <n>, which is newer than the problem supports` | The problem runs on JDKs up to a release below yours. Exit 4 | Select a JDK in the problem's range, as the `fix:` says |
| `cstudy start`, `cstudy test`, `cstudy submit`, `cstudy bench` | `<slug> runs its <language> version on <range>; <source> selects JDK <n>, which is too old` | Your JDK is older than 21, or than the problem's lowest. Exit 4 | Select a newer JDK, or install JDK 25 ([JDK](toolchains.md#jdk)) |
| `cstudy start`, `cstudy test`, `cstudy submit`, `cstudy bench` | `<slug> runs its <language> version on <range>; no JDK was found` | No JDK is installed, or none is on your `PATH`. Exit 4 | Install JDK 25 ([JDK](toolchains.md#jdk)) |
| `cstudy start`, `cstudy test`, `cstudy submit`, `cstudy bench` | `<slug> runs its <language> version on <range>; JAVA_HOME (<path>) holds no JDK` | `JAVA_HOME` is set, and names no JDK. `cstudy` does not look past it. Exit 4 | Point `JAVA_HOME` at a JDK, or unset it |
| `cstudy test --level`, `cstudy submit --level`, `cstudy show --level` | `level <n> is locked; pass level <m> with cstudy test first` | That level is not open yet. A project problem says `cstudy submit`. Exit 3 | Pass every open level first, or ask for an open one |
| `cstudy test --level`, `cstudy submit --level`, `cstudy show --level` | `no level <n>; levels are 1 to <last>` | The problem has no such level. Exit 3 | Ask for a level in the range |
| `cstudy test --level`, `cstudy submit --level`, `cstudy show --level` | `<slug> has no levels` | `--level` is only for problems with levels. Exit 3 | Leave `--level` out |
| `cstudy test`, `cstudy bench` | `<slug> is not autograded` | The attempt is on a `system-design` or `code-review` problem, which no test checks. Exit 3 | Finish it with a rating, such as `cstudy done --rating ok` |
| `cstudy test`, `cstudy submit`, `cstudy bench`, in Python | `` the Python workspace is not set up (python/.venv/bin/python is missing): run `uv sync --directory python` `` | The Python project has no virtual environment. Exit 4 | Run `cstudy doctor --fix`, or the `uv sync` it names |
| `cstudy test --debug` | `cannot debug <language>: port <port> on 127.0.0.1 is already in use; stop the other debug session or choose another port with --debug-port` | Another program, often an earlier debug session, holds the debug port. Exit 4 | Stop that session, or pass another port with `--debug-port` |
| `cstudy test --debug`, in Python | `` cannot debug python: debugpy is not installed in python/.venv; run `uv add --dev debugpy --directory python` `` | The Python project lacks the debugger. Exit 4 | Run the `uv add` it names |
| `cstudy done` | `finish with either --rating easy\|ok\|hard or --gave-up` | It takes one of the two. Exit 3 | `cstudy done --rating ok`, or `cstudy done --gave-up` |
| `cstudy done` | the latest test run did not pass every case; run `cstudy test`, or finish with `--gave-up` | A rating needs a run where every case passed. Exit 3 | Make the tests pass, or finish with `--gave-up` |
| `cstudy done` | `the latest test run passed every case; finish with --rating easy\|ok\|hard` | `--gave-up` is for an attempt that never passed. Exit 3 | Rate it with `--rating` |
| `cstudy done` | the latest test run did not pass level 1; run `cstudy test`, or finish with `--gave-up` | A problem with levels needs at least level 1 passed for a rating. Exit 3 | Pass level 1, or finish with `--gave-up` |
| `cstudy done` | no submission of every unlocked level passed level 1 yet; run `cstudy submit`, or finish with `--gave-up` | A project problem needs a submission that passed level 1 for a rating. Exit 3 | Run `cstudy submit`, or finish with `--gave-up` |
| `cstudy done` | `<slug> is self-graded; finish with --rating easy\|ok\|hard` | A `system-design` or `code-review` problem is graded by your rating alone. Exit 3 | Rate it with `--rating` |
| Any command that reads `config.toml` | `<path>: profile.job_roles: "general" always shows: list the roles you prepare for` | `general` is not a profile value: what any engineer uses shows for every role. An empty list, an unknown value or a value listed twice is refused the same way, by its key. Exit 4 | Correct the key the message names, or leave it out for every value ([job roles and domains](settings.md#job-roles-and-domains)) |
| `cstudy list`, `cstudy next`, `cstudy mock`, `cstudy learn` | `unknown widening "lang"; use role, domain or all` | Only `cstudy list` widens the languages. Exit 3 | Use a value the message names |
| `cstudy learn` | `--domain, --role and --widen apply to the list: cstudy learn --domain <domain>, without a guide or --path` | Those flags narrow the list, and a guide or a path you name shows whatever your profile says. Exit 3 | Leave out the guide or `--path`, or the flags |
| `cstudy start`, `cstudy next --lang`, `cstudy mock --lang` | `<language> is not one of this workspace's languages (<languages>): cstudy lang add <language>` | A new attempt starts only in one of the workspace's languages. An attempt in progress still resumes, and a service project starts anyway. Exit 3 | Run the `cstudy lang add` it names, then `cstudy doctor --fix`; or choose a language it lists |
| `cstudy init --lang`, `cstudy lang` | `unknown language "golang"; use python, typescript, java, kotlin, go or rust` | Nothing was written. Exit 3 | Name one of those six |
| `cstudy lang remove` | `a workspace needs at least one language` | You asked to remove every language it has, and nothing changed. Exit 3 | Keep one, or add another first |
| `cstudy lang remove --delete-folder` | cannot delete `<folder>`: attempt `<id>` (`<slug>`, `<language>`) is in progress; finish it with `cstudy done` or end it with `cstudy abort`, or remove `<language>` without `--delete-folder` | Its files are still in use, and nothing changed. Exit 3 | Finish or abort the attempt, then run it again; or remove the language and keep its folder |
| `cstudy lang remove --delete-folder` | `cstudy lang remove waits until it ends: a run or a job is in progress (process <pid>)` | A test run or a job of this workspace is still going, and nothing changed. Exit 3 | Let it end, or stop it, then run it again |
| `cstudy lang remove --delete-folder` | `cstudy lang remove --delete-folder asks before it deletes; in a script, pass --yes` | There is no terminal to ask you, and no `--yes`; nothing changed. Exit 3 | Run it in a terminal, or add `--yes` |
| `cstudy lang remove --delete-folder` | `<path> leaves the workspace, so cstudy lang remove deleted nothing; remove the link first` | The folder is a link, or leads outside the workspace. Exit 3 | Remove the link yourself, then run it again |
| `cstudy abort` | `cstudy abort waits until it ends: a run or a job is in progress (process <pid>)` | A test run or a job of this workspace is still going, and nothing changed. Exit 3 | Let it end, or stop it with `Ctrl+C` where it runs, then run `cstudy abort` again |
| `cstudy reset` | `cstudy reset waits until it ends: a run or a job is in progress (process <pid>)` | A test run or a job of this workspace is still going, and nothing was deleted. Exit 3 | Let it end, or stop it, then run `cstudy reset` again |
| `cstudy reset` | `type reset to confirm. This can't be undone.` | You typed something other than `reset`, so nothing was deleted. Exit 3 | Run `cstudy reset` again and type `reset`, or pass `--yes` in a script |
| `cstudy import` | `progress.db already holds progress; import needs an empty database` | Import never mixes two histories. Exit 3 | To replace what is there: `cstudy export --out ~/before-import.json`, then `cstudy reset`, then `cstudy import` |
| `cstudy import` | the export uses progress.db schema `<n>`, which is newer than this cstudy (`<m>`); update cstudy first | A newer `cstudy` wrote the export. Exit 3 | Upgrade `cstudy` ([upgrade cstudy](upgrading.md#upgrade-cstudy)) |
| `cstudy solution` | `<slug> is not autograded; --lang, --approach, --all, --explanation-only and --broken apply to autograded problems` | A `system-design` or `code-review` problem has one answer, with no language or approach. Exit 3 | Leave those flags out |

## The AI preview

A refusal of the [AI preview](ai.md) exits 3 and sends nothing. A provider's failure exits 4: [when a request fails](ai.md#when-a-request-fails) lists those messages.

| You see | It means | Do |
|---------|----------|----|
| `AI is off: turn it on with ai.enabled = true (cstudy config edit) or in Settings` | The preview is off, so nothing is sent | Turn it on, if you want it ([turn it on](ai.md#turn-it-on)) |
| `ai.model is not set: choose the model of fixed routing in Settings or with cstudy config edit` | The task's model is not set; under auto routing the message names `ai.fast` or `ai.strong` | Set it to an id that `cstudy ai models <provider>` lists ([routing](ai.md#routing)) |
| `no key for anthropic, which ai.model uses: cstudy ai key anthropic, or Settings` | The task's provider has no key in `credentials.toml` | Run `cstudy ai key anthropic`, or add the key in Settings |
| `AI review needs your consent to send to anthropic:<model id>: run it once at a terminal, or cstudy ai consent anthropic:<model id> --purpose review` | Nothing was ever agreed for this model and purpose, and there is no terminal to ask you | Run it once in a terminal, or record the consent with the command it names ([consent](ai.md#consent)) |
| `not sent` | You answered no, or pressed Enter, at the consent question. Exit 0 | Run it again and answer `y` when you want it sent |
| `the daily token cap is reached: …` | Today's tokens and this request's estimate would pass `ai.daily_token_cap` | Wait until tomorrow, or raise the cap ([the daily token cap](ai.md#the-daily-token-cap)) |
| `credentials.toml would be inside this workspace (<path>): keys never go in a workspace; point CSTUDY_CONFIG at a config.toml outside it` | `CSTUDY_CONFIG` names a `config.toml` inside the workspace, so the keys would be there too | Point `CSTUDY_CONFIG` at a file outside the workspace, or unset it ([keep keys out of repositories](ai.md#keep-keys-out-of-repositories)) |
| `a key is one line of text with no spaces` | The key you typed or piped is empty or holds spaces | Copy the key again, without spaces or a line break inside it |
| `credentials.toml: unknown provider "antropic"`, or another problem of the file, exit 4 | The file does not load: a table other than `anthropic`, `google`, `openai` and `openrouter`, a key other than `api_key`, or an empty value. Nothing but AI work reads it | Correct the file, or delete it and save your keys again with `cstudy ai key` |
| `cstudy doctor` warns: `credentials.toml lies in a Git working tree (<path>)` | Your keys file is inside a Git repository and could be committed | Add `credentials.toml` to that repository's `.gitignore`, or keep your config outside it |
| `your notes are still the template: …`, `… is missing: AI review reads your notes` | AI review reads your answer from the attempt's notes file | Write your answer in the notes file it names, and save it |
| `cstudy ai review is locked during the mock interview (…)` | A mock interview runs | Wait until its timer ends or every problem is done. `--list`, `--show` and `--dismiss` still work |
| In the web UI, AI review says `save your notes first: AI review reads them from disk` | The notes tab has unsaved edits | Save with `Cmd+S`, then choose **AI review** again |

## The web UI

| You see | Do |
|---------|----|
| "This browser has no session with this server" | Open the URL the server printed. The token in it is new every time the server starts |
| `port … is already in use` | Another program holds the port: pick another with `--port`, or leave it out to get a free one |
| `reconnecting…` in the top bar | The page lost the server for a moment and tries again |
| `disconnected` in the top bar | The server stopped or restarted: start it again and open the new URL |
| `cstudy serve` exits 4, or `cstudy doctor` warns on `web ui assets` or `web server` | The page's files or the web server libraries are missing or damaged: reinstall `cstudy` with the command `cstudy doctor` prints, which names the install that runs; if it also warns on `installs`, keep one install first |
| A language is disabled in the Start dialog, with `not in this workspace: cstudy lang add rust` | The workspace does not list it: check it in the **profile** section of Settings and save, or run the command it names ([choose its languages](workspace.md#choose-its-languages)) |
| A language fails in the Health view | Install its toolchain ([toolchains](toolchains.md)), then use **Fix**, on its row or at the top of the view, which runs `cstudy doctor --fix` |
| The dev stack panel says `cstudy dev` is already running in a process | A terminal holds the project's dev stack: stop it there with `Ctrl+C`, or use that one |
| `Tab` skips buttons and links | Your browser moves `Tab` between form fields only: turn on its setting that lets `Tab` reach every button and link |

## Code intelligence

| You see | Do |
|---------|----|
| `not installed: run cstudy doctor --fix` in Settings, or `not installed` in the status bar | Run `cstudy doctor --fix` once, with the network on, then open the file again |
| `stopped: exit 1` in the status bar | The language server ended: choose **Restart**, or run `cstudy doctor` to check the install |
| `no code intelligence for Java: needs JDK 25 or 26` | jdtls runs only on JDK 25 or 26: select one with `JAVA_HOME` ([Java](editor.md#java)) |
| `no code intelligence for Rust: rust-analyzer is not installed` | Run `rustup component add rust-analyzer` ([Rust](editor.md#rust)) |
| `Docker is not running` in the status bar, on a service project | Start Docker, or run the tests once, which starts it; then choose **Restart** |
| `Ctrl+Space` shows nothing | Autocomplete is off, or code intelligence is: turn both on in Settings. With Autocomplete off the editor offers no completion at all |
