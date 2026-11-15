# Spec: Compatibility

What `cstudy` promises to keep working from one release to the next: which surfaces are public, internal or preview, what counts as a breaking change, how a surface is deprecated, how long a release is supported, and the files and tests that hold each promise ([ADR 0027](../decisions/0027-compatibility-contract.md)). It also fixes the identity of content, which progress is keyed on: canonical IDs, problem folders named by slug, and the rubric-checked problems.

## Before 1.0

The promise starts at 1.0.0. Before it, any release may change any surface.

| Rule | Detail |
|------|--------|
| Recording | Every change of a public surface is recorded in `UPGRADING.md` at the repository root, with what to do about it |
| Commits | A change that breaks a public surface is a `feat!:` or `fix!:` commit with a `BREAKING CHANGE:` footer, so the changelog lists it. While the version is `0.x` it bumps the minor version ([versioning](versioning.md#commit-types-and-bumps)) |
| Tests | The [contract tests](#contract-tests) run before 1.0 too: a change of a surface fails them until its snapshot or schema is accepted in the same commit, so no change goes unnoticed |

## Surfaces

| Surface | Class | 1.x promise | Defined by | Enforced by |
|---------|-------|-------------|------------|-------------|
| CLI commands, flags and exit codes | Public | None is removed, renamed or given a new meaning; new ones are additive | `cli/tests/contract/snapshots/commands.json` and `exit-codes.json`; [cli](cli.md) | `cli/tests/contract/test_snapshots.py` |
| `--json` documents | Public, additive only | Fields are never removed, renamed or retyped, and each document has a published JSON Schema | `schemas/cli/<document>.schema.json` ([JSON documents](#json-documents)) | `cli/tests/contract/test_json_documents.py`, `test_json_coverage.py` |
| `--events` stream | Public, versioned | `version` 1 changes only with an incompatible change, and readers ignore unknown event types and fields | `schemas/events.schema.json` (`cstudy test`, `cstudy submit`) and `schemas/dev-events.schema.json` (`cstudy dev`), each `version` 1 | The event tests, such as `cli/tests/entrypoints/commands/test_events.py` and `test_dev_events.py`, and the version in `test_snapshots.py` |
| Workspace layout outside `.cs/` | Public | A 1.0 workspace works with every 1.x. A layout change bumps the marker's `schema` and `cstudy doctor --fix` migrates it; an older cstudy refuses a newer schema | [installation-and-workspaces](installation-and-workspaces.md#layout); the marker in `cli/tests/contract/snapshots/marker.json` | `test_snapshots.py` |
| `progress.db` | Public in behaviour | Every 1.x migrates any earlier 1.x database forward, automatically, after a backup. No downgrade. The tables are not an API for other programs, except the assistance and AI review records, which are public records once they exist | [progress-and-scheduling](progress-and-scheduling.md#schema); [Migrations](#migrations) | `cli/tests/adapters/test_sqlite_upgrades.py` over `cli/tests/fixtures/progress/schema-<N>.sql` |
| Progress export | Public | Any 1.x imports any earlier 1.x export | `schemas/cli/export.schema.json`, `version` 1 | `test_json_documents.py`; the round trips in `test_sqlite_upgrades.py` |
| Config keys and environment variables | Public | Keys and meanings stay; a default may change in a minor release, with a release note | `cli/tests/contract/snapshots/config-keys.json` and `environment.json`; [Environment variables](#environment-variables) | `test_snapshots.py`, `cli/tests/contract/test_environment_variables.py` |
| Your own problems | Public, additive only | A problem that passes `cstudy verify` under 1.0 loads, runs and verifies under every 1.x. New checks apply to catalog content only | `schemas/meta.schema.json`, `schemas/tests.schema.json`, [problem-format](problem-format.md); the problem-format variables of [Environment variables](#environment-variables) | `cstudy verify`; the schema tests in `cli/tests/adapters/test_schema_validation.py` |
| Canonical IDs | Public | A released content ID never changes, since progress is keyed on it. Content itself may be corrected or reworded in any release | The grammar of [Canonical content IDs](#canonical-content-ids) | `cli/tests/domain/test_content_ids.py`; every schema in `schemas/cli/` except `export.schema.json` requires `id` by the grammar |
| Web API, `.cs/`, guide and path formats, the user-docs page format | Internal | They may change in any release. A user-docs page's slug is its canonical ID, `doc/<slug>`, which never changes; its heading ids and front matter may, with a release note | `schemas/web-api.schema.json`, [installation-and-workspaces](installation-and-workspaces.md#layout) (`.cs/`), `schemas/guide.schema.json`, `schemas/path.schema.json`, [user-docs](user-docs.md) | Their own tests, which hold the page and the server together and promise nothing to other programs |
| Human-readable output | Not promised | Scripts use `--json` | Nothing | Nothing |
| AI features | Preview | Their commands, `[ai]` keys and behaviour may change in a minor release. The assistance record and AI review records are public | Their specs, from v0.60 | Their own tests |
| Kotlin code intelligence | Preview | It depends on builds outside cstudy that expire | [web-ui](web-ui.md#code-intelligence-sessions) | Its own tests |

A surface not in this table is internal. Internal names in the code, such as modules, classes and enum members, are not a surface.

## Rules

| Rule | Detail |
|------|--------|
| Breaking changes | Ship only in 2.0. A breaking change makes a 1.x script, workspace, database, export, config file or problem of your own stop working or change meaning |
| Minor releases | Add commands, flags, fields, event types, config keys, problem-format fields, languages and content. A field is added to a document and its schema together |
| Patch releases | Fix bugs and correct content |
| Deprecation | A deprecated public flag, config key, environment variable or JSON field keeps working until 2.0 ([Deprecation](#deprecation)). The warning goes to stderr, never into `--json` or `--events` output |
| Toolchain and platform floors | Python, Node, the JDK, Go, Rust, Docker Engine and OS versions may rise in a minor release when upstream support ends, announced one minor release ahead |
| Support | Fixes land on the latest 1.x minor release |
| Readers | A program that reads a `--json` document, an event or an export ignores the fields and event types it does not know |

## Contract tests

The contract tests live in `cli/tests/contract/` and run with the fast tests.

### Snapshots

Each snapshot is a JSON file in `cli/tests/contract/snapshots/`, written from the live surface:

| Snapshot | Holds | Read from |
|----------|-------|-----------|
| `commands.json` | Every command and subcommand, and for each flag: its names, whether it takes a value, its choices when it is a choice, and `deprecated` | `command_spec` in `entrypoints/command_table.py` |
| `exit-codes.json` | Each exit code by name: the [exit codes](cli.md#exit-codes) of `ExitCode` in `entrypoints/shared.py`, which gains `HANGUP = 129` and `TERMINATED = 143`, the exits of a run or a server that a signal stopped | `ExitCode` |
| `config-keys.json` | Each key of `config.toml`: name, kind, default, choices and whether it is reserved | `domain/config_keys.py` and the parser's key names in `adapters/toml_config.py` |
| `environment.json` | The variable names of each class of [Environment variables](#environment-variables) | `domain/environment_variables.py` |
| `marker.json` | The marker's keys, `schema` and `created_with`, the shape of `[licenses.<key>]`, and `SCHEMA_VERSION` | `adapters/workspace_marker.py` |

`test_snapshots.py` also holds the `version` of `schemas/events.schema.json` and `schemas/dev-events.schema.json` at 1.

A test compares the live surface with its snapshot and reports three lists apart: `removed`, `changed` and `added` entries. An intended change is accepted by writing the snapshots again, from `cli/`:

```bash
CSTUDY_WRITE_SNAPSHOTS=1 uv run pytest -q tests/contract
```

and committing them with the change. A reviewer treats any `removed` or `changed` entry as breaking; `added` entries are additive.

### JSON documents

One schema per document, in `schemas/cli/`, shipped in the wheel under `coding_study/content/schemas/cli/`:

| Document | Command | Schema |
|----------|---------|--------|
| List | `cstudy list --json` | `list.schema.json` |
| Next | `cstudy next --json` | `next.schema.json` |
| Status | `cstudy status --json` | `status.schema.json` |
| History | `cstudy history --json` | `history.schema.json` |
| Set list | `cstudy set list --json` | `set-list.schema.json` |
| Set show | `cstudy set show --json` | `set-show.schema.json` |
| Learn list | `cstudy learn --json` | `learn-list.schema.json` |
| Learn guide | `cstudy learn <guide> --json` | `learn-guide.schema.json` |
| Learn done | `cstudy learn <guide> --done --json` | `learn-done.schema.json` |
| Learn path | `cstudy learn <path> --json` | `learn-path.schema.json` |
| Docs list | `cstudy docs --json` | `docs-list.schema.json` |
| Docs page | `cstudy docs <topic> --json` | `docs-page.schema.json` |
| Test | `cstudy test --json` | `test.schema.json`, with the variants `single-file`, `project` and `service`, told apart by their required fields |
| Submit | `cstudy submit --json` | `submit.schema.json` |
| Stats | `cstudy stats --json` | `stats.schema.json` |
| Doctor | `cstudy doctor --json` | `doctor.schema.json` |
| Progress export | `cstudy export` (the file) | `export.schema.json` |

| Rule | Detail |
|------|--------|
| Dialect | JSON Schema draft 2020-12 |
| Closed objects | Every object sets `additionalProperties: false`, so a field the schema does not name fails the tests. Readers still ignore unknown fields ([Rules](#rules)) |
| Deprecated fields | Carry `"deprecated": true` |
| Validation | `test_json_documents.py` runs each command over the test workspaces and validates its output against its schema; the export is validated from `cstudy export` and from the export fixtures of the upgrade tests |
| Coverage | `test_json_coverage.py` fails when a command or subcommand with a `--json` flag in `command_spec`, or `cstudy export`, has no schema in `schemas/cli/`, or when a file there is used by none |

## Environment variables

Every variable `cstudy` reads or sets is in exactly one class. `domain/environment_variables.py` holds one tuple per class, the readers of the public variables import their names from it, and `environment.json` snapshots the tuples. `test_environment_variables.py` fails when a `"CSTUDY_*"` string literal under `cli/src` is in no tuple.

| Class | Variables | Promise |
|-------|-----------|---------|
| Public (3 of `cstudy`'s own, 4 shared) | `CSTUDY_WORKSPACE`, `CSTUDY_CONTENT`, `CSTUDY_CONFIG` ([cli](cli.md#global-flags), [configuration](cli.md#configuration)); `NO_COLOR`, `VISUAL`, `EDITOR`, `JAVA_HOME`, which `cstudy` reads with their usual meaning | Set by you; the [config keys and environment variables](#surfaces) row |
| Problem format (6) | `CSTUDY_DATA_DIR` in the app container; `CSTUDY_MOCK_CONTROL_URL` and `CSTUDY_MOCK_CONTROL_TOKEN` for `commands.test`; `CSTUDY_RESET_PHASE` for `commands.reset`; `CSTUDY_PROBLEM_DIR` and `CSTUDY_GRADED_LEVEL` for `commands.grade_setup` ([service-projects](service-projects.md#environment), [contract](service-projects.md#contract)) | Set by `cstudy` for user code and problem code; the [your own problems](#surfaces) row |
| Internal (5) | `CSTUDY_EGRESS_HOSTS` (the sandbox's egress probe), `CSTUDY_GO_DEBUG_LISTEN`, `CSTUDY_GO_DELVE` and `CSTUDY_GO_DEBUG_PACKAGE` (cstudy to its Go runner in a debug run of a project), `CSTUDY_HIDDEN_DIRECTORIES` (cstudy to the `hide_paths.cjs` preload of a Node language server, [web-ui](web-ui.md#code-intelligence-sessions)) | None |

The process environment of user code is the allowlist of [runners](runners.md#process-environment). Other variables `cstudy` reads, such as `PATH`, the `XDG_` base directories and the toolchains' own (`GOPATH`, `GRADLE_USER_HOME`, `LLDB_DEBUGSERVER_PATH`), keep the meaning their owners give them, and `cstudy` promises nothing more about them.

## Canonical content IDs

A piece of content is named `<type>/<slug>`:

| Part | Rule |
|------|------|
| `<type>` | `problem`, `guide`, `path`, or `doc` (a page of the [user docs](user-docs.md)) |
| `<slug>` | Matches `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` |
| Namespaces | One per type. Guide and path slugs stay their own namespaces, which the type keeps apart: `guide/hashing` and `path/hashing` are two IDs |
| Stability | A released ID never changes, so neither does its slug |
| In documents | Every object of a `--json` document or a web API response that names content by `slug` carries `id`, the canonical ID, beside it |
| In the progress export | Its rows are database rows and carry `slug` only. The type follows from the table: `attempts`, `schedule` and `bench_runs` name problems, and `guide_reads` names guides |
| Arguments | Commands take slugs, not IDs: `cstudy start two-sum`, `cstudy learn hashing` |

`domain/content_ids.py` defines `ContentType`, `content_id(type, slug)` and `parse_content_id(text)`, which raises `ValueError` on text that does not match the grammar.

## Problem folders

| Rule | Detail |
|------|--------|
| Name | A problem's folder is named by its slug, `problems/<slug>/`, in the content root, in a workspace, in `runners/conformance/` and in the test fixtures (`cli/tests/fixtures/**/problems/`, `cli/tests/fixtures/service_projects/`). The name equals `slug` in `meta.yaml` |
| No number | `meta.yaml` has no `id`, and `schemas/meta.schema.json` does not allow one. Nothing orders, names or selects problems by a number |
| Text | Docs, code and tests name a folder `problems/<slug>`. `CHANGELOG.md` and `docs/reviews/` are records and keep the names of their time; an ADR keeps its decision text, and its paths and links follow the folders |
| `cstudy new` | Writes `problems/<slug>/`, in the checkout or in the workspace |

### Order

| Where | Order |
|-------|-------|
| `cstudy list`, with your own problems overlaid | The catalog before your own problems; then track, in `Track` order (`dsa`, `practical`, `lld`, `concurrency`, `debugging`, `system-design`, `code-review`, `behavioral`); then the taxonomy position of the primary pattern, problems without patterns first within their track; then `order`; then slug |
| `cstudy next`, among eligible problems | Difficulty, then `order`, then slug ([selection](progress-and-scheduling.md#cstudy-next-selection)) |

### Your own problems

A folder of your workspace named `NNNN-<slug>`, as `cstudy new` wrote them before, is reported, not migrated. A directory under `<workspace>/problems/` whose name is not a valid slug is not loaded as a problem: `cstudy verify` (check S2) fails on it, and `cstudy doctor` warns on its workspace files row. Both name each such directory with the rename to make, a command run from the workspace root, `mv problems/<name> problems/<slug>`, where `<slug>` is the `slug` of its `meta.yaml`, or, when that cannot be read, the name without its leading `NNNN-`. The marker stays `schema = 1`.

## Rubric-checked problems

The system design and code review exercises are problems of the kinds `system-design` (10) and `code-review` (6), with `track` equal to `kind`. Your answer is checked against a rubric, by you; nothing grades it automatically.

| Rule | Detail |
|------|--------|
| Folder | `problems/<slug>/` with `meta.yaml`, `prompt.md`, `rubric.md`, `reference.md`, `template.md`, and for code review `change.diff` or `files/` |
| Notes | Your answer stays at `notes/<track>/<slug>.md` in the workspace |
| Catalog only | Rubric problems load from the content root only. A workspace's own `problems/` folder with a rubric kind is a content error: `rubric problems are catalog-only` |
| `behavioral` | Stays a track value and holds no content |
| `tracks/` | Gone, with `schemas/item.schema.json`. Its track notes are in [content](content.md) and the self-graded loop in the user docs' practice page |

### Schema

`schemas/meta.schema.json` validates every problem:

| Part | Rule |
|------|------|
| Always required | `slug`, `title`, `status`, `difficulty`, `track`, `kind` |
| `track`, `kind` | Both enums gain `system-design` and `code-review` |
| An autograded kind (`function`, `design`, `progressive`, `concurrent`, `project`) | Requires `comparator` and `approaches`, and keeps every signature, levels, project and concurrency condition of today, all under this branch |
| A rubric kind (`system-design`, `code-review`) | Requires `estimate_minutes` and `track` equal to `kind`; allows `references.study_guides`; forbids `signature`, `comparator`, `approaches`, `patterns`, `levels`, `perf`, `stub`, `languages`, `jdk`, `hang_guard_ms`, `project`, `concurrency`, `summary`, `guides` and `references.leetcode` |

### Loading

| Rule | Detail |
|------|--------|
| Owners | The problem repository and the rubric repository both read `problems/`. A folder's `kind` decides which one owns it; each treats the other's folders as absent |
| Files | The problem files list every folder |
| `cstudy verify --changed` | Selects changed rubric problems too |
| Kinds in the code | `ProblemKind` stays autograded only. `EntryKind` has `SYSTEM_DESIGN` and `CODE_REVIEW` in place of `ITEM`, and `RUBRIC_KINDS` is the test for a rubric problem. The word "item" is not shown in output, docs or the page |

## Checked by

How a problem is checked is derived from its folder, not written in `meta.yaml`:

| Value | When |
|-------|------|
| `tests` | Every autograded kind |
| `rubric` | The folder has `rubric.md` |
| `ai-review` | Reserved for v0.60; no problem has it yet |

So the 8 `lld` problems with a `rubric.md` are `tests` and `rubric`, rubric problems are `rubric`, and the rest are `tests`.

| Surface | Detail |
|---------|--------|
| JSON | `checked_by`, an array in that order, on the problem entries of `cstudy list`, `cstudy next` and `cstudy status`, and of the web API |
| Filter | `cstudy list --checked-by tests` or `--checked-by rubric` |
| The page | A Checked by column on the Problems view, showing `tests`, `tests + rubric` or `rubric`, in the default columns where ID was, and a `checked` filter |

### No ID column

The ID column is gone from the `cstudy list` table and from the Problems view. The preference reader drops a stored `id` from `problem_columns` without a word, so an existing `.cs/serve/preferences.json` keeps loading.

## Migrations

`progress.db` migrates forward on the first command that opens it, and with `cstudy doctor --fix` ([progress-and-scheduling](progress-and-scheduling.md#schema)).

| Case | Behaviour |
|------|-----------|
| Schema N, 1 ≤ N < latest | Under the migration lock and before the first script runs, `cstudy` copies the database with SQLite's online backup API to `<workspace>/.cs/backups/<db stem>-schema-<N>-<UTC yyyymmddThhmmssZ>.db`, adding `-2`, `-3`, ... on a name clash, and checks that the copy reads schema N. Then it migrates, and prints one line on stderr: `progress.db: backed up to .cs/backups/<file>; migrated from schema N to M`. `cstudy doctor --fix` reports the same in its notice |
| A fresh database (N = 0) | Migrates with no backup |
| The backup fails | Nothing is changed: `BackupError`, exit 4, `cannot back up progress.db before migrating it: <reason>; nothing changed` |
| A script fails after the backup | Under the same lock, `cstudy` writes the copy back over `progress.db` with the online backup API and checks that it reads schema N, then fails: `MigrationError`, exit 4, `migrating progress.db from schema N failed at schema M: <reason>; restored it from .cs/backups/<file>`, where M is the script that failed. An interrupt restores the copy the same way and then ends the command as it would have. When the restore fails too, the message says so and names the copy to put back by hand: `migrating progress.db from schema N failed at schema M: <reason>, and restoring it failed: <reason>; copy .cs/backups/<file> over progress.db`. The next attempt copies schema N again |
| Schema newer than this `cstudy` reads | Refused before any read or write: `UsageError`, exit 3, `progress.db uses schema N, newer than the M this cstudy reads: upgrade cstudy`. No downgrade |
| Backups | Kept, never pruned. `cstudy reset` keeps `.cs/backups/`, and the workspace's `.gitignore` already ignores `/.cs/*`, so they stay out of version control |

### Upgrade tests

| Item | Rule |
|------|------|
| Fixtures | `cli/tests/fixtures/progress/schema-<N>.sql`, plain SQL, for each schema N from 1 to the latest, today 7. Each applies migrations 1 to N and inserts at least one row into every table that exists at N, covering every `mode` and `status` value, and the JSON of `schedule.levels` from N = 6 |
| Coverage | A test fails when the latest migration has no fixture |
| Upgrades | For each N below the latest, through the store's first use and through `cstudy doctor --fix`: the schema is the latest; one backup exists, reads schema N and holds the fixture's rows; every fixture row survives with its values, and new columns are NULL. The latest fixture opens as it is, with no backup |
| Round trips | For each N, an export of the migrated database imports into an empty database, and exporting that gives the same document except `exported_at`. An export built at schema N imports into the latest schema with every row |

## Deprecation

A deprecated flag, config key or environment variable keeps working, and prints one line on stderr, at most once per name per process:

```text
warning: <name> is deprecated since cstudy <version> and is removed in 2.0; use <replacement>
```

`; use <replacement>` is there only when the deprecation has a replacement. Nothing goes to stdout, so `--json` and `--events` output is unchanged. A deprecated JSON field has no runtime warning; its schema marks it `"deprecated": true`.

| Part | Rule |
|------|------|
| Registry | `DEPRECATIONS` in `domain/deprecations.py`: entries `Deprecation(surface, name, since, replacement)`, `surface` one of `flag`, `config_key`, `env_var`, `json_field`, and `replacement` optional |
| Names | A flag is `cstudy <command> [<subcommand>] --<flag>`; a config key its dotted TOML name; an environment variable its name; a JSON field `<document>.<path>`, the schema's file name without `.schema.json` and the field's dotted path through properties, arrays left out |
| Flags | A deprecated flag stays as a hidden option that warns, and its value is merged with its replacement's. `commands.json` marks it `deprecated: true`. A command declares it with `deprecated_flag(deprecation)` from `entrypoints/shared.py`, which takes the flag from the entry's name and warns when the command line gives it, and uses `merged(replacement, deprecated)` for the value: the replacement's, unless the command line left it unset |
| Config keys, variables | `load_environment` warns about each deprecated key present in the config file and each deprecated variable that is set (`warn_about_deprecated_use` in `adapters/deprecation_warnings.py`). The warning is all it does: the code that reads the key or variable keeps reading it |
| Tests | `cli/tests/domain/test_deprecations.py` and `cli/tests/entrypoints/test_deprecation_warnings.py` use registries of their own. `cli/tests/contract/test_deprecations_table.py` holds `DEPRECATIONS` and the table below equal, and each `json_field` entry marked in its schema |

### Deprecations

One row per entry of `DEPRECATIONS`, in its order; with none, the one row `None yet`.

| Surface | Name | Since | Replacement |
|---------|------|-------|-------------|
| None yet | | | |
