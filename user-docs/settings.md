---
title: Settings and preferences
summary: Your config.toml, which every command reads, the web UI's preferences, and how to back up, restore or reset your progress.
section: Settings and help
order: 120
---

# Settings and preferences

`cstudy` has two kinds of settings:

| Kind | Where | Covers |
|------|-------|--------|
| Your configuration | `config.toml`, one file for all your workspaces | The default language, time limits, the review schedule and more. Every command reads it |
| Preferences | `.cs/serve/preferences.json`, in each workspace | How the web UI looks and behaves: Vim keys, the theme, run on save, code intelligence |

The **Settings** view of the web UI (`Alt+7`) edits both. In the terminal, `cstudy config` finds and opens the file.

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
| `default_lang` | `"python"` | The language of `cstudy start`, `cstudy next` and `cstudy mock` when you give no `--lang`: `python`, `typescript`, `java`, `kotlin`, `go` or `rust` |
| `open_on_start` | `true` | Open your editor on `cstudy start` |
| `progress_db` | `"progress.db"` | Where your progress lives, relative to the workspace |
| `next.tracks` | `["dsa"]` | The tracks `cstudy next` and `cstudy mock` pick from |
| `time_limit.enabled` | `false` | Turn time limits on for every run, as `cstudy test --time-limit` does for one |
| `bench.reps` | `7` | Timed repetitions per size in `cstudy bench` |
| `schedule.max_interval_days` | `180` | No review is scheduled further away than this |
| `schedule.mastered_interval_days` | `21` | A problem counts as mastered from this review interval on |

The `[schedule]` table also holds the first intervals of each rating (`ok_first_interval_days`, `easy_first_interval_days` and the like). A new interval applies to reviews scheduled from then on: dates already set do not move. The Settings view lists every key, with its name in the file, its value, its default and when a change applies.

A change applies at the next command. The web UI reads the file for each request, so it needs no restart, except after a change to `progress_db`: restart `cstudy serve` then.

### Change `progress_db`

Changing `progress_db` moves nothing: your data stays in the old file, and `cstudy` uses the file at the new path, or starts an empty one there. Settings asks first and says whether a database exists at the new path, and `cstudy config edit` says so once you close your editor.

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

Beside the preferences, or below them in a narrow window, the view edits `config.toml`. Each key shows a friendly label with its name in the file beside it, so a search of the page finds either. **Save** writes only what you changed and keeps your comments; empty a field to return it to its default. A value `cstudy` would refuse is refused here too, by the key's name, and nothing is written to the file. Save covers both places, and if one fails it says which and keeps those changes unsaved, while the other's stay saved.

## Back up and restore your progress

Your progress lives in `progress.db`, which the workspace's `.gitignore` leaves out. Back it up as a JSON file you can commit:

```bash
cstudy export                         # writes progress-export.json at the workspace root
cstudy export --out ~/backup.json
cstudy import                         # restores progress-export.json into an empty progress.db
cstudy import ~/backup.json
```

`cstudy import` refuses a database that already holds progress, so it never mixes two histories. The Progress view of the web UI (`Alt+5`) has export and import too.

## Start over

`cstudy reset` in the terminal, or **Reset progress…**, the red button in the **danger** section of Settings, deletes your progress in this workspace: attempts, scheduled reviews, bench runs, run folders and rendered statements. You see what goes, with counts, before anything does. It can't be undone, so you type `reset` to confirm. It refuses while a run or a job is active. Run `cstudy export` first if you may want your progress back.

```bash
cstudy reset                    # progress only
cstudy reset --files            # also your practice files, project folders and notes
cstudy reset --files --archive  # and .archive/, the files of earlier attempts
```

Your practice files, project folders and notes stay unless you tick that box, or pass `--files`. `.archive/` stays unless you tick its own, or pass `--archive`. Your settings, toolchains, language servers, your own problems and your [sets](planning.md#problem-sets) always stay. A reset ends an open attempt along with the rest: the menu of attempts in progress empties at once, and a tab that was showing that attempt says it ended and turns read-only. `--yes` skips the question, for a script with no one to type.
