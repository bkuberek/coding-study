> **Draft.** This guide becomes final in 1.0.0.

# Upgrading from cstudy 0.x to 1.0

This page lists every change of a public surface on the way to 1.0, release by release, with what to do about it. For the steps of an upgrade itself (upgrade `cstudy`, then `cstudy doctor --fix`), read [Upgrading cstudy](user-docs/upgrading.md), or run `cstudy docs upgrading`.

## Before you upgrade

Export your progress, so you have a copy you can restore into any version:

```bash
cstudy export   # writes progress-export.json at the workspace root
```

## What changed in 0.51

Your progress is not affected: it is keyed on slugs, and no slug changed.

### Problem folders are named by slug

A problem's folder is `problems/<slug>/`, and `meta.yaml` has no `id`. No problem has a number any more. `cstudy new` writes `problems/<slug>/`.

Your own problems made by an earlier `cstudy new` are named `problems/NNNN-<slug>/` and have an `id:` line. They no longer load. `cstudy doctor` warns about each one on its `workspace files` row, and `cstudy verify` fails check S2 on it. Both print the fix, for example:

```text
from the workspace root run `mv problems/5001-my-queue problems/my-queue`, then delete the `id:` line of `problems/my-queue/meta.yaml`
```

What to do: run each `mv` it prints, from the workspace root, and delete the `id:` line of each `meta.yaml`. When the slug is taken by another folder, it says so: give the problem a free slug instead. Then run `cstudy doctor` again.

### System design and code review are problems

The 16 system design and code review exercises are problems of the kinds `system-design` and `code-review`. They sit in `problems/<slug>/` with the other problems, and you check your answer against a rubric. Your notes stay at `notes/<track>/<slug>.md`.

What to do: replace `cstudy list --kind item` with `--kind system-design` or `--kind code-review`. `--kind item` is gone.

A rubric problem comes from the catalog only. A folder of your own `problems/` with one of these kinds is a content error, `rubric problems are catalog-only`.

### `tracks/` is gone

`tracks/` and `schemas/item.schema.json` are gone from the content.

What to do, only if you keep a content root of your own (`--content` or `CSTUDY_CONTENT`): move each `tracks/<track>/<slug>/` to `problems/<slug>/`, rename its `item.yaml` to `meta.yaml`, and add `kind:` with the same value as its `track:`.

### `id` in JSON is the canonical ID

Every object of a `--json` document that names content by `slug` carries `id` beside it: `problem/<slug>`, `guide/<slug>`, `path/<slug>` or `doc/<slug>`. In `cstudy list --json`, `id` used to be the problem's number, such as `"0001"`, or null for a system design or code review exercise:

```text
before: {"id": "0001", "slug": "two-sum", "kind": "function", ...}
after:  {"id": "problem/two-sum", "slug": "two-sum", "kind": "function", "checked_by": ["tests"], ...}
```

What to do: a script that read the number reads `slug`, or `id` as an opaque name. There is no numeric id. Commands still take slugs: `cstudy start two-sum`. The progress export is unchanged: its rows carry `slug`.

The web API of `cstudy serve` carries the same `id`. It is internal ([What 1.0 promises](#what-10-promises)).

### `kind` values

`kind` in `cstudy list --json`, `cstudy next --json`, `cstudy status --json` and `cstudy history --json` is `system-design` or `code-review` where it was `item`.

What to do: a script that tested for `item` tests for those two values.

### Checked by

Problem entries of `cstudy list --json`, `cstudy next --json` and `cstudy status --json` carry `checked_by`: `["tests"]`, `["tests", "rubric"]` for the `lld` problems with a rubric, or `["rubric"]`. `cstudy list --checked-by tests` and `--checked-by rubric` filter by it.

What to do: nothing. Programs that read these documents ignore fields they do not know.

### The ID column is gone

The `cstudy list` table has no ID column. On the Problems page of `cstudy serve`, the **checked by** column takes its place in the default columns, and **more** has a **checked** filter.

What to do: if you chose your own columns, the saved list drops `id` without a word and keeps the rest. Add **checked by** from the `columns` menu if you want it.

### Order

`cstudy list` lists the catalog, then your own problems, each by track, primary pattern, `order` and slug, never by number. System design and code review problems sit in their tracks' place. `cstudy next` breaks a tie by difficulty, `order` and slug.

What to do: nothing, unless a script relies on the order of `cstudy list --json`.

### Set entries are slugs

Each entry of `sets.yaml` is a problem's slug, alone or as `{slug: ..., level: ...}`. An entry that is not a slug is refused, exit 4:

```text
sets.yaml: set backend-loop: "Two_Sum" is not a slug
```

What to do: if you edited `sets.yaml` by hand, fix the entry it names.

### A backup before every migration

Before `cstudy` migrates `progress.db` to a newer schema, it copies it to `.cs/backups/` and prints one line:

```text
progress.db: backed up to .cs/backups/<file>; migrated from schema <n> to <m>
```

If the copy fails, nothing changes and the command exits 4. If the migration fails, `cstudy` puts the copy back over `progress.db`, says so, and exits 4. Backups are kept: `cstudy` never deletes one, and `cstudy reset` leaves them.

What to do: nothing. Delete old backups by hand when you no longer want them.

### A newer `progress.db` is refused

A `cstudy` older than the one that last migrated your `progress.db` refuses it before it reads or writes anything, and exits 3:

```text
error: progress.db uses schema <n>, newer than the <m> this cstudy reads: upgrade cstudy
```

What to do: upgrade `cstudy`, or [roll back](#how-to-roll-back) the database too.

### Exit codes 129 and 143

Exit 129 means a hangup (SIGHUP) stopped a `cstudy test --debug` run. Exit 143 means SIGTERM stopped a `cstudy test` or `cstudy submit` run with `--events`, a `cstudy test --debug` run, or `cstudy serve`. Both are in the [exit codes](docs/specs/cli.md#exit-codes).

What to do: a script that checks exit codes treats 129 and 143 as it treats 130, an interrupt.

### Deprecation warnings

A deprecated flag, config key or environment variable keeps working until 2.0, and prints one line on stderr:

```text
warning: <name> is deprecated since cstudy <version> and is removed in 2.0; use <replacement>
```

Nothing goes to stdout, so `--json` and `--events` output is unchanged. Nothing is deprecated yet.

What to do: when you see the warning, switch to the replacement it names.

### JSON Schemas

The `--json` documents and the progress export have JSON Schemas in [`schemas/cli/`](schemas/cli/), shipped with `cstudy`.

What to do: nothing. Validate your scripts' input against them if you like.

## What 1.0 promises

From 1.0.0, every 1.x release keeps these working:

- Commands, flags and exit codes: none is removed, renamed or given a new meaning.
- `--json` documents: fields are only added, never removed, renamed or retyped.
- The `--events` stream: `version` 1 changes only with an incompatible change.
- Your workspace and `progress.db`: a 1.0 workspace works with every 1.x, and a newer 1.x migrates the database forward, after a backup.
- Progress exports: any 1.x imports an export from any earlier 1.x.
- Config keys and the variables `CSTUDY_WORKSPACE`, `CSTUDY_CONTENT` and `CSTUDY_CONFIG`: their names and meanings stay.
- Your own problems: one that passes `cstudy verify` under 1.0 loads, runs and verifies under every 1.x.
- Canonical IDs: a released ID never changes.

A breaking change waits for 2.0. A deprecated name keeps working until then, with a warning. The web API, `.cs/` and the text output are not promised: scripts use `--json`. AI features and Kotlin code intelligence are previews, which may change in a minor release.

The full contract: [Compatibility](docs/specs/compatibility.md).

## How to roll back

1. Install the previous version, with its release tag. Homebrew installs only the latest, so for an older version uninstall it (`brew uninstall cstudy`) and use uv or pipx:

   ```bash
   uv tool install --force git+https://github.com/bkuberek/coding-study@v0.50.0
   # or: pipx install --force git+https://github.com/bkuberek/coding-study@v0.50.0
   ```

2. If the upgrade migrated `progress.db`, put the old database back. Stop `cstudy serve` and any run first. You have two ways:

   - **The backup.** It is the file the migration line named, `.cs/backups/progress-schema-<n>-<yyyymmddThhmmssZ>.db`, where `<n>` is the old schema and the time is UTC. Move `progress.db` aside, then copy the backup in its place. If `progress.db-wal` or `progress.db-shm` sit beside it, move them aside too:

     ```bash
     mv progress.db progress.db.newer
     cp .cs/backups/progress-schema-6-20261115T093000Z.db progress.db
     ```

   - **An export.** Move `progress.db` aside the same way, then restore an export made before the upgrade. `cstudy import` makes a new `progress.db` and restores into it:

     ```bash
     cstudy import
     ```

   The backup holds your progress up to the upgrade, and an export up to when you made it. Progress made after either is lost. If you set `progress_db` in `config.toml`, use that file in place of `progress.db`.

3. An older version loads your own problems by its own rules. Before 0.51, a problem's folder is `problems/NNNN-<slug>/` and its `meta.yaml` has an `id:` line.

## 0.52 to 1.0

This section fills in as each release ships.

### The learner profile

The learner profile is the default filter of `cstudy list`, `cstudy next`, `cstudy mock` and `cstudy learn`, and of the Problems, Guides and Mock views of `cstudy serve`: the languages you practice, the job roles you prepare for and the domains you study. Each defaults to all of its values. Read [the learner profile](docs/specs/cli.md#the-learner-profile).

Nothing changes for your workspace until you choose. A workspace whose marker has no `languages` has all six languages, and `cstudy doctor`, `cstudy doctor --fix`, the IDE files and `cstudy start` behave as before: Python, TypeScript, Java and Kotlin required, Go and Rust optional. With that marker and a config file without `[profile]` keys, the profile filters nothing, so every list and pick shows what it showed before.

What to do: nothing. When you want fewer languages or a narrower list, choose them.

### Workspace languages

`cstudy init --lang <language>` (repeatable) creates a workspace with those languages' folders only, and `cstudy lang` changes them later:

```bash
cstudy lang list                         # the languages and their folders
cstudy lang add go                       # writes go/ and go.work, then: cstudy doctor --fix
cstudy lang remove rust                  # keeps rust/ on disk
cstudy lang remove rust --delete-folder  # deletes rust/ after a question; --yes skips it
```

They are written to the marker as `languages = ["python", "go"]`. The marker's `schema` stays 1. Once a workspace lists its languages:

- `cstudy doctor` shows and `--fix` runs only those languages' rows and steps, and a chosen Go or Rust is required, so it fails when missing. A `languages` row names them.
- The IDE files hold only those languages' settings, extensions and debug configurations.
- A new attempt in another language exits 3, with the command that adds it: `rust is not one of this workspace's languages (python, go): cstudy lang add rust`. An attempt in progress still resumes. Service projects start whatever the languages.
- `cstudy verify` skips the other languages, each with `not one of this workspace's languages: cstudy lang add <language>`.
- Removing a language never deletes progress, `.archive/`, `projects/` or `notes/`.

An older `cstudy` ignores `languages`: its `cstudy doctor` reports the folders of the languages you left out as missing, and its `cstudy doctor --fix` writes them.

### Job roles and domains in `config.toml`

Two keys, set with `cstudy config edit` or in Settings:

```toml
[profile]
job_roles = ["backend", "platform"]   # leave the key out for every role
domains = ["backend", "security"]     # leave the key out for every domain
```

An empty list, an unknown or repeated value, and `general` in `job_roles` are config errors. `general` is not a profile value: an entry labeled `general` matches every role profile.

What to do: nothing, unless you want them.

### `--widen` and the profile line

While the profile narrows a list, these commands apply it by default:

| Command | New flags |
|---------|-----------|
| `cstudy list` | `--widen lang\|role\|domain\|all` |
| `cstudy next` | `--widen role\|domain\|all` |
| `cstudy mock` | `--domain`, `--role`, `--widen role\|domain\|all` |
| `cstudy learn` | `--domain`, `--role`, `--widen role\|domain\|all` |

`--widen` is repeatable and drops the profile in that dimension for one run, without changing it. An explicit `--lang`, `--role` or `--domain` replaces the profile in its dimension. `--set` ignores the profile.

While the profile hid at least one entry, the human output ends with one dim line on standard output:

```text
filtered by your profile: 120 of 400 problems · languages python, go · --widen all shows all 400
```

What to do: a script that reads the human output of these commands drops the last line when it starts with `filtered by your profile:`, or reads `--json`, which never prints it.

### `profile` in `--json`

`cstudy list --json`, `cstudy next --json` and `cstudy learn --json` carry `profile`: the values that narrowed the rows, by dimension, null where a dimension narrowed nothing, and `hidden`, the entries the profile left out (`{"problems": 280}`, or `{"guides": 92, "paths": 11}` in `learn`). Guides in `cstudy learn --json` carry `domains` and `job_roles`.

What to do: nothing. The fields are added; with no profile set, the entries are the same as before and every `hidden` count is 0.

### Guides need `domains` and `job_roles`

Every guide's `meta.yaml` lists `domains` and `job_roles`, and `cstudy verify` fails a guide without them.

What to do, only if you keep a content root of your own (`--content` or `CSTUDY_CONTENT`) with guides of your own: add both lists to each guide's `meta.yaml`, as [the guide format](docs/specs/guides.md#metayaml) describes.

### The AI preview

An optional preview sends requests to an AI model with your own key: AI review of the system design and code review problems, and a check of your models ([ai](docs/specs/ai.md), or run `cstudy docs ai`). It is off by default, and with it off nothing leaves the machine. Its commands, `[ai]` keys and human output are preview surfaces, which may change in a minor release; the AI review record is public.

| What | Change |
|------|--------|
| Commands | `cstudy ai` with `status`, `usage`, `key`, `models`, `consent`, `check` and `review` |
| `config.toml` | Six keys in `[ai]`: `enabled` (default `false`), `routing`, `model`, `fast`, `strong` and `daily_token_cap` (default `500000`) |
| Keys | `credentials.toml`, beside `config.toml`, written with mode `0600` by `cstudy ai key` and Settings. `cstudy` never reads or writes it inside a workspace |
| `progress.db` | Schema 8 adds `ai_reviews`, `ai_calls` and `ai_consents`, after the usual backup. A `cstudy` older than this one refuses the migrated database |
| Export and import | The export holds `ai_reviews` and has `schema_version` 8, so an older `cstudy` refuses it; it leaves out `ai_calls` and `ai_consents`, which `cstudy import` neither reads nor checks. `cstudy import` refuses a database that holds an AI review, as it does one with any progress. `cstudy reset` empties all three tables |
| `checked_by` | The rubric problems are `["rubric", "ai-review"]` in `cstudy list --json`, `cstudy next --json`, `cstudy status --json` and `cstudy set show --json`, whatever the settings. `cstudy list --checked-by` takes `ai-review` |
| `cstudy doctor` | An `ai` row, only while `ai.enabled` is true or `credentials.toml` exists; it warns and never fails |
| `cstudy serve` | The AI section in Settings, and, with AI on, AI review on a rubric problem's Attempt view; the Problems page's Checked by column reads `rubric + AI review` |

What to do: nothing, unless you want the preview. A script that tested `checked_by` for exactly `["rubric"]` tests whether it holds `"rubric"`; `--checked-by rubric` lists the same problems as before. Never put a key in your workspace or a repository; if you keep `config.toml` in a dotfiles repository, add `credentials.toml` to its `.gitignore`.
