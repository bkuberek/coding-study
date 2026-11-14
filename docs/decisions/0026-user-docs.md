# ADR 0026: User docs are shipped content in `user-docs/`, read with `cstudy docs` and the Docs view

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-14 |
| Spec | [user-docs](../specs/user-docs.md), [cli](../specs/cli.md#cstudy-docs), [web-ui](../specs/web-ui.md#docs-view), [installation-and-workspaces](../specs/installation-and-workspaces.md#content-root) |
| Builds on | [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0015](0015-local-web-ui.md), [ADR 0025](0025-concept-guides-and-learning-paths.md) |

## Context

How to use `cstudy` was written in four places: the README, `docs/guides/web-ui.md`, `docs/guides/toolchains.md`, and the website's own pages, which a separate session rewrote by hand after each release and which drifted from what `cstudy` does. The web UI had no help at all, and the terminal had none beyond `--help`. The owner asked for one source of user documentation, shipped with the package, shown in the web UI and in the terminal, and ready for the website to copy, as it already copies the catalog's counts.

## Decision

### One folder of Markdown pages, shipped as content

`user-docs/` sits at the content root beside `guides/`, one `<slug>.md` per topic, and ships in the sdist and in the wheel at `coding_study/content/user-docs/`. Each page starts with YAML front matter, `title`, `summary`, `section` and `order`, which `schemas/user-doc.schema.json` validates. Front matter, not a separate index file: a page carries everything about itself, and static site generators read it as it is.

The folder is flat and holds no images. A page is plain CommonMark with tables, so it reads the same in the terminal, the page, GitHub and the website; the screenshots stay with the README in `docs/images/`, where they cost the wheel nothing.

It is not a guide: a guide teaches an idea and has examples run by a test, diagrams and reading progress, while a user page says what to type and what you see, and records nothing. The pattern is the guides' where it fits: a content folder, a schema, static checks in `cstudy verify`, a command, a view.

### Read with `cstudy docs` and the Docs view

`cstudy docs` lists the topics by section, `cstudy docs <topic>` prints one, rendered by Rich on a terminal and as Markdown text otherwise, and `--json` gives the index the website can read. No workspace is needed, since a user reads the docs before having one. `--open` serves the page on the topic, as `cstudy learn --open` does for a guide.

The web UI gains a Docs view, eighth in the top bar (`Alt+8`): the pages by section with a search over their passages, and a page rendered on the server like every other Markdown the page shows, with a deep link to each heading, `#/docs/<slug>/<id>`. The search runs in the page over the listing it already loaded, as the Problems view's does, so no search index ships and typing asks the server nothing.

### The pages are checked against the command line

A user page is wrong in a way a reader cannot see when it names a flag that was renamed. `cstudy verify` checks the docs as it checks the guides (D1 to D6), and D6 reads every `cstudy` command in a page's shell blocks and inline code and checks the command, its subcommand and each flag against `cstudy`'s own Click command tree. A fast test runs D6 over the shipped pages, so a change to the command line fails until the pages follow.

Facts that are not commands, such as a default or what a view shows, are checked by the author against the code and the specs when the page is written, as the specs are.

### The website copies the pages of a release

The website reads `user-docs/` at a release tag, with the front matter for order and groups and `cstudy docs --json` as an index. Links between pages are `<slug>.md#<id>` with GitHub's heading ids, which the website maps to its own URLs. A page's slug, its headings' ids and its front matter are its interface.

## Consequences

- The README shrinks to the install, the first steps and a link to the docs; `docs/guides/web-ui.md` and `docs/guides/toolchains.md` move into `user-docs/`. Each leaves a short page at its old path that links to the new one, since released versions of `cstudy` link there from the fixes `cstudy doctor` prints.
- `cstudy doctor` links to `user-docs/toolchains.md` on GitHub, by the same section ids as before.
- The wheel grows by the pages' text, about 100 KB.
- The top bar has eight views; the web UI's bundle gains the Docs view's chunk, fetched when it first opens.
- An author who changes a command or a flag changes the pages that name it in the same commit, or the fast tests fail.
