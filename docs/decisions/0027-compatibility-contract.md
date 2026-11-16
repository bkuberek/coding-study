# ADR 0027: A compatibility contract held by snapshots and schemas, and content named `<type>/<slug>`

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-14 |
| Spec | [compatibility](../specs/compatibility.md) |
| Amends | [ADR 0020](0020-catalog-labels.md) (labels are on problems; the former items are rubric-checked problems), [ADR 0021](0021-ai-reviewed-problems.md) (R11's first consumers, the 10 system-design and 6 code-review items, are rubric-checked problems) |
| Builds on | [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0013](0013-homebrew-distribution.md), [ADR 0015](0015-local-web-ui.md), [ADR 0025](0025-concept-guides-and-learning-paths.md), [ADR 0026](0026-user-docs.md) |

## Context

1.0.0 is the first release under a compatibility promise: scripts, workspaces, databases, exports, config files and problems of your own keep working across 1.x. The roadmap's "Compatibility promise" was the only statement of it, and nothing held it:

- No document said which surfaces are public, internal or preview, what counts as breaking, how deprecation works or how long a release is supported.
- Only the event stream and the web API had schemas. Commands, flags, exit codes, config keys, environment variables, the workspace marker and the `--json` documents could change without any test noticing.
- `progress.db` migrated in place on the first command that opened it, with no backup, one upgrade path was tested, and an older `cstudy` wrote to a newer database.
- Nothing helped deprecate a flag, key or field.

Content identity was not settled either, and 1.0 freezes it, since progress is keyed on it. Problem folders carried a 4-digit number that `meta.yaml` repeated, and the number ordered `cstudy list`, broke ties in `cstudy next`, filled an ID column and was a preference value. The system design and code review exercises were "items" under `tracks/`, with their own schema, repository and kind. Guides, paths and user docs had slugs and no common name.

## Decision

### Surfaces, rules and the pre-1.0 rule

The [compatibility spec](../specs/compatibility.md#surfaces) takes the roadmap's table row for row and names, for each surface, the file that defines it and the test that holds it. Breaking changes ship only in 2.0; minor releases add; patch releases fix; toolchain floors rise in a minor release, announced one ahead; fixes land on the latest 1.x minor. Before 1.0.0 any release may change any surface, and `UPGRADING.md` records each change of a public surface.

### Snapshots and schemas hold the surfaces

The command tree, the exit codes, the config keys, the environment variables and the marker are JSON snapshots in `cli/tests/contract/snapshots/`, compared with the live surface by the fast tests. A difference is reported as `removed`, `changed` and `added` entries, and an intended one is accepted by writing the snapshots again with `CSTUDY_WRITE_SNAPSHOTS=1`. A reviewer reads a `removed` or `changed` entry as breaking. Snapshots, not hand-written lists: the test writes them, so they cannot drift from the code, and the diff in review is the change.

Every `--json` document and the export get a JSON Schema in `schemas/cli/`, shipped in the wheel, with closed objects (`additionalProperties: false`) so a field added without its schema fails the tests. Readers are told to ignore unknown fields, which keeps adding a field a minor change. A coverage test ties every `--json` flag to a schema.

### Three classes of environment variables

Public variables are the ones you set: `CSTUDY_WORKSPACE`, `CSTUDY_CONTENT` and `CSTUDY_CONFIG`, and `NO_COLOR`, `VISUAL`, `EDITOR` and `JAVA_HOME` with their usual meaning. The variables `cstudy` sets for user code and problem code belong to the problem format. Every other `CSTUDY_*` variable is internal. One module holds the three lists, and a test fails on a `CSTUDY_*` name in the source that none holds.

### Deprecation warns on stderr only

A deprecated flag, config key or environment variable keeps working until 2.0 and prints one `warning:` line on stderr per process, with the replacement when there is one. A deprecated JSON field has no runtime warning: its schema marks it `"deprecated": true`, since a warning could only go where the document goes. The registry is empty, and the spec's Deprecations table, which a test holds equal to it, reads "None yet".

### Canonical IDs, `<type>/<slug>`

Content is named `<type>/<slug>`, with the types `problem`, `guide`, `path` and `doc`. The type keeps the guide and path namespaces apart, so no slug is renamed. The ID is a field `id` beside `slug` in every `--json` and web API object that names content. Commands keep taking slugs; accepting IDs as arguments is additive and can come later.

### Problem folders named by slug, with no number

Every problem folder is `problems/<slug>/` and `meta.yaml` has no `id`. A number that only orders and names folders is a second identity to keep unique, and the catalog has one already. `cstudy list` orders by catalog, track, primary pattern, `order` and slug, and `cstudy next` breaks ties by difficulty, `order` and slug. The ID column goes from the list and the page.

A workspace folder of your own named `NNNN-<slug>` is reported by `cstudy verify` and `cstudy doctor` with the `mv` to run, not migrated: it is your folder, under your version control, and the marker stays `schema = 1`.

### The items become rubric-checked problems

The 10 system design and 6 code review items are problems of the kinds `system-design` and `code-review` in `problems/`, validated by `meta.schema.json` with a branch per kind family. `tracks/` and `item.schema.json` go. One folder, one schema and one ID space for everything you practice, and the word "item" leaves what you see. Rubric problems come from the catalog only. The Python modules that load them keep their names, which are not a surface.

### Checked by

How a problem is checked is derived from its folder: `tests` for every autograded kind, `rubric` when it has `rubric.md`. It is `checked_by` in the JSON, a `--checked-by` filter, and a Checked by column on the Problems view in place of ID. `ai-review` is reserved for [ADR 0021](0021-ai-reviewed-problems.md)'s work.

### A backup before every migration, and no downgrade

Before migrating a database of schema N ≥ 1, `cstudy` copies it with SQLite's online backup API into `.cs/backups/`, checks the copy, and stops with nothing changed when the backup fails. Backups are never pruned: they are small, and a deleted backup cannot be restored. A database newer than `cstudy` reads is refused before any read or write. A fixture of every schema migrates forward in the tests, and exports round-trip from every schema.

## Consequences

- Every change of a command, flag, exit code, config key, environment variable, marker key or `--json` field shows in review as a snapshot or schema diff, before 1.0 as after it.
- The release that renames the folders, drops the numbers and turns the items into problems is breaking: each is a `feat!:` commit with a `BREAKING CHANGE:` footer, and `UPGRADING.md` says what to do, including renaming numbered problems of your own.
- `id` in the JSON documents changes meaning, from a problem's number to its canonical ID.
- [ADR 0020](0020-catalog-labels.md)'s labels apply to problems, rubric-checked ones included; [ADR 0021](0021-ai-reviewed-problems.md)'s first consumers are the rubric-checked problems.
- `.cs/backups/` grows by one copy of `progress.db` per migration.
- An older `cstudy` can no longer write to a database a newer one migrated.
