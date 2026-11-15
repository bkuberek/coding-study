> **Draft.** This guide becomes final in the 1.0 release candidates.

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
