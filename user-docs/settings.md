---
title: Settings and preferences
summary: Your config.toml, which every command reads, your learner profile, the AI section, the web UI's preferences, and how to back up, restore or reset your progress.
section: Settings and help
order: 120
---

# Settings and preferences

`cstudy` has four kinds of settings:

| Kind | Where | Covers |
|------|-------|--------|
| Your configuration | `config.toml`, one file for all your workspaces | The default language, the job roles and domains of your [learner profile](#your-learner-profile), time limits, the review schedule and more. Every command reads it |
| The workspace's languages | `.cs/workspace.toml`, in each workspace | The languages you practice there: its folders, the toolchains `cstudy doctor` checks, its IDE files, and the languages of your learner profile ([choose its languages](workspace.md#choose-its-languages)) |
| Preferences | `.cs/serve/preferences.json`, in each workspace | How the web UI looks and behaves: Vim keys, the theme, run on save, code intelligence |
| AI keys | `credentials.toml`, beside `config.toml`, never in a workspace | Your own provider keys for the optional [AI preview](ai.md#your-keys) |

The **Settings** view of the web UI (`Alt+7`) edits all four. In the terminal, `cstudy config` finds and opens the file, `cstudy lang` changes the languages, and `cstudy ai key` saves a key.

## Your configuration

The file is `~/.config/coding-study/config.toml`, or `$XDG_CONFIG_HOME/coding-study/config.toml` when that variable is set. `CSTUDY_CONFIG` points `cstudy` at another file. Every key is optional: a missing file means every default.

```bash
cstudy config path    # print where the file is
cstudy config edit    # open it in $VISUAL or $EDITOR
```

`cstudy config edit` makes the file from a commented template when you have none: every key at its default, with what it does, so it reads as the defaults until you uncomment a line. It never changes a file you already have.

The keys you are most likely to change:

| Key | Default | Does |
|-----|---------|------|
| `default_lang` | `"python"` | The language of `cstudy start`, `cstudy next` and `cstudy mock` when you give no `--lang`: `python`, `typescript`, `java`, `kotlin`, `go` or `rust`. When it is not one of the workspace's languages, the first of them is used |
| `open_on_start` | `true` | Open your editor on `cstudy start` |
| `progress_db` | `"progress.db"` | Where your progress lives, relative to the workspace |
| `next.tracks` | `["dsa"]` | The tracks `cstudy next` and `cstudy mock` pick from |
| `profile.job_roles` | every role | The job roles you prepare for ([your learner profile](#your-learner-profile)) |
| `profile.domains` | every domain | The domains you study |
| `time_limit.enabled` | `false` | Turn time limits on for every run, as `cstudy test --time-limit` does for one |
| `bench.reps` | `7` | Timed repetitions per size in `cstudy bench` |
| `schedule.max_interval_days` | `180` | No review is scheduled further away than this |
| `schedule.mastered_interval_days` | `21` | A problem counts as mastered from this review interval on |

The `[schedule]` table also holds the first intervals of each rating (`ok_first_interval_days`, `easy_first_interval_days` and the like). A new interval applies to reviews scheduled from then on: dates already set do not move. The Settings view lists every key, with its name in the file, its value, its default and when a change applies, and [configuration keys](commands.md#configuration-keys) lists every key with its default. The `[ai]` table holds the six keys of the AI preview, which is off by default ([turn it on](ai.md#turn-it-on)).

A change applies at the next command. The web UI reads the file for each request, so it needs no restart, except after a change to `progress_db`: restart `cstudy serve` then.

### Change `progress_db`

Changing `progress_db` moves nothing: your data stays in the old file, and `cstudy` uses the file at the new path, or starts an empty one there. Settings asks first and says whether a database exists at the new path, and `cstudy config edit` says so once you close your editor.

### Point to your study guides

Study guides are notes of your own; `cstudy` ships none. The rubric problems, those of the `system-design` and `code-review` tracks, can name sections of them in `references.study_guides`, as paths relative to one folder of yours. Set that folder as `root` in the `[study_guides]` table:

```toml
[study_guides]
root = "~/study-guides"   # an absolute path, or one that starts with ~/
```

It is unset by default, and then no study guide is linked. With it set, `cstudy start` and `cstudy show` end a rubric problem's statement with a `## Study guides` section, a link to each referenced file that exists under the root, and `cstudy start` prints a `guide` line for each:

```text
guide      file:///home/me/study-guides/distributed-systems-study-guide.md#databases
```

A referenced file that is not under the root is left out, and nothing fails. The bundled rubric problems name sections of `distributed-systems-study-guide.md`, so a guide of yours saved at that path under the root is linked. In the Settings view the key is **Study guides folder**.

## Your learner profile

Your learner profile is the default filter of the lists you choose from: the languages you practice, the job roles you prepare for and the domains you study. `cstudy list`, `cstudy next`, `cstudy mock` and `cstudy learn` apply it, and so do the Problems, Guides and Mock views of the web UI. Each part defaults to every value, so a profile you never set filters nothing.

| Part | Values | Stored in | Change it with |
|------|--------|-----------|----------------|
| Languages | `python`, `typescript`, `java`, `kotlin`, `go`, `rust` | The workspace's marker, `.cs/workspace.toml` | `cstudy init --lang`, `cstudy lang add` and `cstudy lang remove` ([choose its languages](workspace.md#choose-its-languages)), or Settings |
| Job roles | The roles of the [labels](problem-kinds.md#labels), except `general` | `profile.job_roles` in `config.toml` | `cstudy config edit`, or Settings |
| Domains | The domains of the labels | `profile.domains` in `config.toml` | `cstudy config edit`, or Settings |

### Job roles and domains

```toml
[profile]
job_roles = ["backend", "platform"]   # leave the key out for every role
domains = ["backend", "security"]     # leave the key out for every domain
```

Each key is a list of one or more values, each listed once. Leaving a key out means every value, including the values a later `cstudy` adds; a list that names every value today does not take the new ones. An empty list, an unknown value, a value listed twice and `general` are refused, by the key's name, as any wrong key is. `general` marks what any engineer uses, and those problems and guides show whatever roles you list. Keep `algorithms` among your domains for the data structures and algorithms problems.

A change applies at the next command. A page that is open reads it after a reload, or at once when you save it in its own Settings.

### What it filters

| Part | An entry matches when |
|------|-----------------------|
| Languages | It has a reference in one of your languages. A system design or code review problem, which has no language, always matches |
| Job roles | It lists one of your roles, or `general`. A problem of your own without labels matches |
| Domains | It lists one of your domains, or none |

An entry shows when it matches every part the command applies. A guide matches by its own domains and roles, and a path when one of its steps does; `cstudy learn` applies the roles and domains only, since a guide teaches in every language.

The profile does not apply to your [sets](planning.md#problem-sets), to `cstudy stats`, `cstudy history` and the reviews of the Progress view, to `cstudy verify`, to a command given a slug, a guide or a path, or to these docs: what you chose and what you did stay visible. Outside a workspace, `cstudy list` and `cstudy learn` use all six languages, and your roles and domains still apply.

### Widen it for one run

```bash
cstudy list --widen lang          # every language, this once
cstudy list --widen all           # the whole catalog
cstudy next --widen role          # a pick from every role
cstudy learn --domain security    # this domain instead of yours
```

`--widen` drops the profile in one part for one run, and repeats; it never changes the profile. `cstudy list` takes `lang`, `role`, `domain` or `all`. `cstudy next`, `cstudy mock` and `cstudy learn` take `role`, `domain` or `all`, since a pick starts only in one of the workspace's languages, and a guide has no language. An explicit `--role` or `--domain` replaces the profile in its part and may name a value outside it; `--role backend` then keeps the entries that list `backend`, without `general`. The `--lang` of `cstudy list`, `cstudy next` and `cstudy mock` replaces your languages the same way.

While the profile hides something, the command ends with one dim line that says how much shows, what narrowed it and how to see the rest:

```text
filtered by your profile: 82 of 400 problems · languages python, go · roles backend and general · domains security, backend · --widen all shows all 400
```

`cstudy next` and `cstudy mock` count the problems the pick came from (`picked from 52 of 125 problems`), and `cstudy learn` counts guides and paths. A profile that hides nothing prints no line. When the profile leaves nothing to pick, `cstudy next` and `cstudy mock` say so and name `--widen all`. `--json` prints no line: its document holds `profile`, with the values that narrowed the list and `hidden`, the number of entries the profile left out.

In the web UI, the filters of each view show the profile and widen it ([filters and your profile](web-ui.md#filters-and-your-profile)).

## Preferences

Preferences are stored in `.cs/serve/preferences.json` in the workspace, so they follow the workspace, not the browser.

| Preference | Default | Effect |
|------------|---------|--------|
| Vim keybindings | off | Vim keys in every editor; `:w` saves |
| Run on save | off | Each save, from the page or from your IDE, runs the tests again, as `cstudy test --watch` does |
| Type-check TypeScript | on | TypeScript runs type-check, so type errors show in the editor |
| Theme | system | Light or dark, or follow your system |
| Code intelligence | off | Live errors, hover documentation and go to definition from a language server on your computer; needs `cstudy doctor --fix` once ([details](editor.md#code-intelligence-and-autocomplete)) |
| Autocomplete | off | Completion and signature help, while code intelligence is also on. Off, the editor offers no completion at all |

## The Settings view

Nothing in **Settings** applies until you choose **Save** in the bar at the top, which stays on screen as you scroll: it shows how many changes you have, and **Reset** undoes all of them. The theme previews as you pick it. Leaving with unsaved changes asks first. The `vim` and `theme` switches in the status bar still apply at once.

The **profile** section heads the view ([below](#the-profile-section)), then the **AI** section ([the AI section](#the-ai-section)). Beside the preferences, or below them in a narrow window, the view edits `config.toml`. Each key shows a friendly label with its name in the file beside it, so a search of the page finds either. **Save** writes only what you changed and keeps your comments; empty a field to return it to its default. A value `cstudy` would refuse is refused here too, by the key's name, and nothing is written to the file. Save covers every place: it writes `config.toml`, then `credentials.toml`, then the workspace's languages, then the preferences, and if one fails it says which and keeps those changes unsaved, while the others stay saved.

### The Profile section

The **profile** section edits your [learner profile](#your-learner-profile), with a checkbox for each language, job role and domain. The languages are this workspace's, stored in `.cs/workspace.toml`; the roles and domains are in `config.toml`, for all your workspaces. A workspace that never chose its languages shows all six checked, marked `all six (none chosen)`. The last checked language cannot be unchecked, since a workspace needs at least one, and unchecking every role or every domain is refused. Under the languages, the section names the `cstudy lang` command that Save runs.

After Save adds a language, the status line says that **Fix** in the Health view installs its toolchain files, as `cstudy doctor --fix` does. The Problems, Guides and Mock views use the saved profile from then on.

### Removing a language

A Save that removes a language first asks what becomes of the language's folder, before it writes anything:

| Choice | Does |
|--------|------|
| **Keep the folder** | Removes the language and leaves its folder and your practice files on disk, as `cstudy lang remove rust` does. It is the default |
| **Delete the folder…** | Shows what goes, each folder with its number of practice files, any shared folder that stays and why, and what always stays, then asks again: **Delete rust/** deletes it, as `cstudy lang remove rust --delete-folder` does, and **Back** returns to the first question. It can't be undone |
| **Cancel** | Saves nothing, and keeps your changes for another try. Escape does the same |

While an attempt in that language is in progress, **Delete rust/** is disabled, with the reason beside it; keeping the folder still works. Progress, `.archive/`, `projects/` and `notes/` always stay ([choose its languages](workspace.md#choose-its-languages)).

### The AI section

The **AI (preview)** section sets up the optional [AI preview](ai.md). It shows whether AI is on or off, since it is where you turn it on, and each group names where it is stored:

| Group | Stored in | Holds |
|-------|-----------|-------|
| **Turn on** | `config.toml` | The `ai.enabled` checkbox |
| **Keys** | `credentials.toml` | A row per provider, `key set` or `no key`, with a field for a new key and **Remove**. A key you type is saved by **Save** and never shown again |
| **Models** | `config.toml` | The routing, `fixed` or `auto`, then `ai.model`, or `ai.fast` and `ai.strong`, and the daily token cap. **Load models** beside a provider with a key lists its model ids as suggestions, as `cstudy ai models` does; **Check** runs `cstudy ai check`, after the consent dialog when it needs one |
| **This workspace** | `progress.db` | Your consents, each with **Revoke**, then today's usage and the last 7 days |

**Load models** and **Check** use what is saved, so they are disabled, with the reason beside them, while AI is off or a change is staged. **Revoke** acts at once, without Save: it only makes `cstudy` ask again next time.

## Back up and restore your progress

Your progress lives in `progress.db`, which the workspace's `.gitignore` leaves out. Back it up as a JSON file you can commit:

```bash
cstudy export                         # writes progress-export.json at the workspace root
cstudy export --out ~/backup.json
cstudy import                         # restores progress-export.json into an empty progress.db
cstudy import ~/backup.json
```

`cstudy import` refuses a database that already holds progress, so it never mixes two histories. The Progress view of the web UI (`Alt+5`) has export and import too. An export keeps your AI reviews, and leaves out your AI requests and consents, which belong to this machine.

## Start over

`cstudy reset` in the terminal, or **Reset progress…**, the red button in the **danger** section of Settings, deletes your progress in this workspace: attempts, scheduled reviews, bench runs, AI reviews, AI requests and consents, run folders and rendered statements. You see what goes, with counts, before anything does. It can't be undone, so you type `reset` to confirm. It refuses while a run or a job is active. Run `cstudy export` first if you may want your progress back.

```bash
cstudy reset                    # progress only
cstudy reset --files            # also your practice files, project folders and notes
cstudy reset --files --archive  # and .archive/, the files of earlier attempts
```

Your practice files, project folders and notes stay unless you tick that box, or pass `--files`. `.archive/` stays unless you tick its own, or pass `--archive`. Your settings, your AI keys, toolchains, language servers, your own problems and your [sets](planning.md#problem-sets) always stay. A reset ends an open attempt along with the rest: the menu of attempts in progress empties at once, and a tab that was showing that attempt says it ended and turns read-only. `--yes` skips the question, for a script with no one to type.
