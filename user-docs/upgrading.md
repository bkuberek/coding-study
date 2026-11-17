---
title: Upgrading cstudy
summary: Upgrade cstudy, bring your workspace up to date with cstudy doctor --fix, keep your own files, choose your languages and profile when you want, see what the AI preview changes, and move a workspace to a new machine.
section: Start here
order: 45
---

# Upgrading cstudy

An upgrade changes `cstudy` and the content that ships with it: the problems, the guides and the runners. Your workspace stays yours. After most upgrades, one command brings it up to date: `cstudy doctor --fix`.

## Upgrade cstudy

Upgrade with the tool you installed `cstudy` with:

```bash
brew upgrade cstudy            # Homebrew
uv tool upgrade coding-study   # uv
pipx upgrade coding-study      # pipx
cstudy --version               # the version that runs now
```

The `installs` row of `cstudy doctor` names the install that runs. When several copies of `cstudy` are on your `PATH`, only the first one runs, so upgrade that one, or keep one and remove the others first ([several installs](doctor.md#several-installs)).

## After you upgrade

1. Before you upgrade, if you like, export your progress. The upgrade makes its own copy of `progress.db` before it changes it, so this is a second copy, one you can commit or keep elsewhere ([back up and restore](settings.md#back-up-and-restore-your-progress)):

   ```bash
   cstudy export
   ```

2. Check the workspace. Whatever the new version needs set up shows as `WARN` or `FAIL`, each row with its `fix:`:

   ```bash
   cstudy doctor
   ```

3. Bring the workspace up to date:

   ```bash
   cstudy doctor --fix
   ```

4. If you open the workspace in VS Code or IntelliJ IDEA, refresh its IDE files. It updates the files it wrote and keeps the ones you edited ([what stays yours](#what-stays-yours)):

   ```bash
   cstudy ide
   ```

Run them inside the workspace, or pass `--workspace PATH`. If you skip `cstudy doctor --fix`, the next command that runs code refreshes the runners, and the next one that opens `progress.db` migrates it; `--fix` does it all at once, with each project's setup.

## What doctor refreshes

In a workspace, `cstudy doctor --fix` does this, then checks again:

| What | `--fix` |
|------|---------|
| The runner runtime | Brings `.cs/runtime/` in line with the new content. It belongs to `cstudy`, not to you |
| Template files | Writes each file the workspace lacks, such as the project of a language added since you made the workspace. It never overwrites a file, and writes only the folders of the workspace's languages |
| `progress.db` | Migrates an older database to the current schema, after copying it to `.cs/backups/` |
| The projects | Runs each project's setup again: `uv sync`, `pnpm install` and the Gradle warm-up ([set up and repair](doctor.md#set-up-and-repair-with---fix)) |
| Language servers | Installs or updates them, only while code intelligence is on ([the editor](editor.md#turn-them-on)) |

The migration prints one line:

```text
progress.db: backed up to .cs/backups/<file>; migrated from schema <n> to <m>
```

`cstudy` keeps every backup: it never deletes one, and `cstudy reset` leaves `.cs/backups/` alone. If the copy fails, nothing changes and the command stops with exit 4. If the migration fails, `cstudy` puts the copy back over `progress.db`, says so, and exits 4 ([errors by command](troubleshooting.md#errors-by-command)).

With code intelligence off, `--fix` installs no language server and says so:

```text
skipped the language servers: code intelligence is off; turn it on in Settings of cstudy serve, then run cstudy doctor --fix again
```

It stays quiet when every language server it installs is in place already.

## What stays yours

| Yours | What an upgrade does |
|-------|----------------------|
| Practice files, notes, project folders, your own problems and your sets | Nothing. `cstudy doctor --fix` writes only missing files, so it never overwrites one you edited |
| IDE files you edited | `cstudy ide` rewrites an IDE file only while it is as `cstudy` wrote it. One you edited stays, with a warning, until you run `cstudy ide --force` |
| Starter files of a project folder | They stay as you started them, even when a newer `cstudy` changes the starter. `cstudy start <slug> --restore <file>` writes the starter's version of one file back |
| `config.toml` | Nothing. A key that a new version adds takes its default until you set it |
| `credentials.toml` | Nothing. Your AI keys stay where they are, beside `config.toml` |
| `progress.db` | Migrated to the current schema, with a copy in `.cs/backups/` first |

What `cstudy` refreshes is its own: `.cs/` (the runner runtime, caches and language servers), `.venv` and `node_modules`.

## Older workspaces

A workspace made by an older `cstudy` keeps working with a newer one. What the newer version adds, such as a language's project or the `projects/` folder, shows in `cstudy doctor` as a `WARN` until `cstudy doctor --fix` writes it. An older `progress.db` migrates as above. Your own problems in `problems/` that load as no problem, such as a folder whose name is not its slug, make the `workspace files` row warn, with the fix to make for each.

The other way round does not work. A `cstudy` older than the one that last wrote your workspace or `progress.db` refuses it before it reads or writes anything, and exits 3:

```text
error: the workspace at <path> uses schema <n> (created with cstudy <version>); this cstudy reads schema <m>: upgrade cstudy
error: progress.db uses schema <n>, newer than the <m> this cstudy reads: upgrade cstudy
```

`cstudy doctor` shows the same as a `FAIL` on its `workspace` or `progress database` row. Upgrade `cstudy` to the version that wrote them, or a newer one ([upgrade cstudy](#upgrade-cstudy)). `cstudy` never moves a database back to an older schema.

## Languages and the learner profile

Nothing changes until you choose. A workspace keeps all six languages until you narrow them, and a [learner profile](settings.md#your-learner-profile) you never set filters nothing, so after an upgrade every list, pick and `cstudy doctor` row is what it was.

To practice fewer languages, remove the others, then check the workspace again:

```bash
cstudy lang remove java kotlin rust   # their folders stay on disk
cstudy doctor
```

From then on `cstudy doctor` checks only the languages you kept, and requires each of them, Go and Rust included ([choose its languages](workspace.md#choose-its-languages)). Your roles and domains are two keys of `config.toml`, or the **profile** section of Settings ([job roles and domains](settings.md#job-roles-and-domains)).

Once your profile hides something, `cstudy list`, `cstudy next`, `cstudy mock` and `cstudy learn` end their output with a line that starts with `filtered by your profile:`. A script that reads their text can drop that line, or read `--json`, which never prints it.

The languages are kept in the workspace's marker, `.cs/workspace.toml`. A `cstudy` older than the one that added them ignores them: its `cstudy doctor` reports the folders of the languages you removed as missing, and its `cstudy doctor --fix` writes them back.

## The AI preview

The [AI preview](ai.md) stays off after an upgrade, and nothing is sent until you turn it on. Two things change for everyone:

| What | Change |
|------|--------|
| `progress.db` | Migrates to schema 8, after its copy in `.cs/backups/`, as every migration does. Schema 8 adds three empty tables: AI reviews, AI requests and AI consents. A `cstudy` older than this one then refuses the database ([older workspaces](#older-workspaces)) |
| Checked by | The system design and code review problems are checked by `rubric` and `ai-review`, whatever your settings: `checked_by` is `["rubric", "ai-review"]` in `--json` output, and the web UI's Checked by column reads `rubric + AI review`. `cstudy list --checked-by rubric` lists the same problems as before |

A script that tested `checked_by` for exactly `["rubric"]` tests whether it holds `rubric` instead. `cstudy export` writes the AI reviews and leaves out the AI requests and consents, which belong to this machine; an export made after the upgrade has schema 8, so an older `cstudy` refuses to import it. `cstudy doctor` shows an `ai` row only once AI is on or `credentials.toml` exists, so its output is as before until then.

## Move to a new machine

Your progress lives in `progress.db`, which the workspace's `.gitignore` leaves out, so carry it as an export. On the old machine:

```bash
cstudy export   # writes progress-export.json at the workspace root
```

Commit and push the workspace with the export, or copy the workspace folder. Then, on the new machine:

1. Install `cstudy`, the same version or a newer one ([install cstudy](getting-started.md#install-cstudy)), and the toolchains of the languages you practice ([toolchains](toolchains.md)).

2. Clone the workspace, set it up, and restore your progress into its new, empty `progress.db`:

   ```bash
   git clone <your-repository> ~/cstudy-workspace
   cd ~/cstudy-workspace
   cstudy doctor --fix
   cstudy import
   ```

If you copied `progress.db` along, skip `cstudy import`: your progress is there already, and `cstudy import` refuses a database that holds progress. An export from a newer `cstudy` is refused too: upgrade first.

The web UI's preferences stay behind, since they live in `.cs/serve/preferences.json`. Turn code intelligence on again in Settings if you use it, then run `cstudy doctor --fix` once more to install its language servers.

Your AI keys are in neither the workspace nor the export, and neither are your AI consents and usage. If you use the [AI preview](ai.md), save your keys again on the new machine with `cstudy ai key`; its first AI request there asks for your consent again.

## What changed

Every release has its notes on [the releases page](https://github.com/bkuberek/coding-study/releases), and [the changelog](https://github.com/bkuberek/coding-study/blob/main/CHANGELOG.md) lists every change, version by version. Read them before an upgrade to see which commands, flags or files changed.
