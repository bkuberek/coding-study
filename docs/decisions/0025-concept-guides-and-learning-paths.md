# ADR 0025: Concept guides and learning paths are content beside the problems, read with `cstudy learn`

| Field | Value |
|-------|-------|
| Status | Accepted. The pilot is built: the format, the checks, `cstudy learn` and the path "Hashing", with seven guides. The page's Guides view is next |
| Date | 2026-11-11 |
| Spec | [guides](../specs/guides.md), [cli](../specs/cli.md#cstudy-learn), [authoring](../specs/authoring.md#guides-and-paths), [problem-format](../specs/problem-format.md#metayaml) (`guides`), [installation-and-workspaces](../specs/installation-and-workspaces.md#content-root), [progress-and-scheduling](../specs/progress-and-scheduling.md#schema) (`guide_reads`) |
| Amends | [PRD](../prd.md): FR-18 joins |
| Builds on | [ADR 0004](0004-original-problem-wording.md), [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0020](0020-catalog-labels.md), [ADR 0023](0023-problem-sets.md) |

## Context

The owner, on 2026-11-11: cstudy is becoming a study app, not just practice. Problems, tests, hints, solutions and reviews train a skill you already have the idea for; nothing teaches the idea first. The owner's bar for the teaching: "make sure the information is accurate and goes into enough depth, with examples, and diagrams".

The audience runs from beginner to expert, where a beginner is new to the topic, not to programming: someone who can write a function in one language. A guide starts plainly and goes deep.

Three questions were open: where the guides live, what a first path covers, and how reading is recorded.

## Decision

### Guides and paths are a content folder of their own

`guides/` sits at the content root beside `problems/` and `tracks/`, and ships in the sdist and in the wheel at `coding_study/content/guides/`. A guide is not a problem (it has no tests and no attempts) and not an item (an item is answered and graded against a rubric), so neither folder fits it. A content root without `guides/` simply has no guides.

| Path | Holds |
|------|-------|
| `guides/<slug>/meta.yaml` | Title, summary, level (`intro`, `core` or `advanced`), prerequisites, related guides, and the problems that practise it |
| `guides/<slug>/guide.md` | The guide: a fixed set of sections, diagrams as Mermaid, examples embedded from `examples/` |
| `guides/<slug>/examples/` | Runnable programs, each embedded in `guide.md` with its output |
| `guides/paths/<slug>.yaml` | A path: a title, a summary and ordered steps, each a guide or a problem, with an optional level target for a progressive or project problem |

A guide's slug is its folder's name, and a path's is its file's name, so neither repeats it. `schemas/guide.schema.json` and `schemas/path.schema.json` validate the YAML, and `cstudy verify --static` runs [checks of their own](../specs/guides.md#static-checks) next to the problems': every reference resolves, prerequisites form no cycle, a path puts a guide's prerequisites first, every example is embedded verbatim and has its output, and every diagram has its accessibility lines and a current text rendering.

A problem links back with an optional `guides:` list in its `meta.yaml`, which must name guides that exist.

### Diagrams are Mermaid, with a text rendering made when the guide is written

A diagram is a fenced `mermaid` block in `guide.md`, with `accTitle` and `accDescr`. There are no image files. GitHub draws the block, the page's Guides view will draw it with a bundled renderer, and the terminal shows a text drawing instead.

The text drawing is made when the guide is written, not when it is read, so a user installs nothing. `tools/guides/` pins [beautiful-mermaid](https://github.com/lukilabs/beautiful-mermaid) 1.1.3 (MIT) as a development dependency, and its script writes, right after each `mermaid` block, a marker carrying the SHA-256 of the block's source and a `text` block with the drawing. A static check fails a drawing whose marker no longer matches its source, so a changed diagram cannot ship with a stale drawing. The text renderer draws flowcharts, state, sequence, class and ER diagrams, so guides use only those types.

### Examples are run by a test

Every example is a real program in `examples/`, embedded in `guide.md` byte for byte, with its output in an `output` block after it. A content test runs each one and compares what it prints with that block, so an example cannot rot. Python examples and JavaScript ones run in the fast suite; Go and Java ones are marked slow, and each language skips where its toolchain is missing.

### Reading is marked, not inferred

`cstudy learn <guide> --done` marks a guide read; printing it does not, since printing is not reading. The mark lives in `progress.db`, in a new table, `guide_reads`, so `cstudy reset` empties it and `cstudy export` carries it like every other record of what you did. A path's progress is computed each time: a guide step is done when the guide is read, a problem step when the problem has a passed attempt through every level it has, and a step with a level target when an attempt has passed that level.

### The web UI is where guides read best; the terminal reads them all

The owner, on 2026-11-11: recommend the web UI for learning, and keep full CLI support. The Guides page of `cstudy serve` is the recommended way to read: Mermaid drawn, navigation between guides, and a path's progress beside its steps. It is the next step and is not built here.

The terminal is fully supported. `cstudy learn` lists the guides and the paths; `cstudy learn <guide>` renders a guide's Markdown with Rich on a terminal, and prints it as Markdown text when its output is not a terminal, its diagrams as their text drawings either way; `cstudy learn --path <path>` shows a path's steps and what is done. Each takes `--json`. Reading needs no workspace; `--done` does. The list and a guide end with one quiet line that points to the web UI, `cstudy learn <guide> --open`. Until the Guides page lands, `--open` says plainly that the page comes with the next step: keeping the flag now means the hint and the scripts that use it do not change when the page arrives.

### The first path: "Hashing: from your first hash map to tamper-evident ledgers"

Seven guides, from what a hash function is to Merkle proofs, around the thirteen problems of the catalog that practise hashing. It covers one topic from its first idea to an expert's, which is the shape every later path takes.

## Consequences

- Guide text carries facts about languages and libraries. Each guide cites the official documentation for them in its "Further reading", and the pilot's claims are listed with their sources for an independent review.
- Authors run one more tool when they change a diagram: `pnpm install` and `pnpm render` in `tools/guides/`, which needs Node.js and pnpm, as the web UI's sources already do. Readers need neither.
- beautiful-mermaid depends on elkjs (EPL-2.0 or GPL-3.0-or-later). It stays in `tools/guides/node_modules/`, a development tool that is never committed or shipped; only its output, the text drawings, is.
- A guide's examples are content code that runs on the author's machine in tests, never in a user's workspace.
- `progress.db` gains migration 0007, `CREATE TABLE IF NOT EXISTS`, so it is safe to renumber again. Its number leaves 0006 to the level-passes work, which takes it. An older cstudy's `cstudy doctor` reports such a database as newer than it knows, as after every migration.

## Later options

| Option | What it would add |
|--------|-------------------|
| The page's Guides view (next) | Guides and paths in `cstudy serve`, drawing Mermaid with a locally bundled, lazily loaded renderer that follows the page's theme, and hiding the text drawings; `cstudy learn <guide> --open` opens a guide there |
| Concept checks | Short questions per guide on the review schedule |
| Mastery per level | Path progress that reads per-level passes once they land |
| `verify --changed` for guides | Only the guides and paths a branch changed |

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Guides inside `problems/` | A guide teaches an idea that several problems practise, so it belongs to none of them |
| Guides as items in `tracks/` | Items are answered and graded; a guide is read |
| Front matter in `guide.md` | GitHub shows front matter as a table above the guide, and the problems already keep their metadata in `meta.yaml` |
| Hand-drawn SVG files | Two sources per diagram, and the terminal could not show them |
| Rendering Mermaid at read time | A user would need Node.js and a renderer to read a guide in the terminal |
| Marking a guide read when it is printed | Printing is not reading, and a mark you did not mean is noise in a path |
| A file in `.cs/` for reading progress | `cstudy reset` and `cstudy export` would need rules of their own for it, while a table in `progress.db` gets theirs for free |
