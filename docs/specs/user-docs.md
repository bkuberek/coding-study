# Spec: User docs

The **user docs** are how to use `cstudy`: installing it, setting up a workspace, working on a problem, the web UI, settings and what to do when something fails. They are one set of Markdown pages in `user-docs/`, shipped with `cstudy` like the problems and the guides, read in the terminal with [`cstudy docs`](cli.md#cstudy-docs), in the web UI's [Docs view](web-ui.md#docs-view), on GitHub as plain files, and copied by the website ([ADR 0026](../decisions/0026-user-docs.md)).

The specs and ADRs stay where they are: they say how `cstudy` is built, for its developers. A user page says what a user does and sees.

The pages are written for everyone from beginner to expert, where a beginner is new to the topic: plain, short sentences in our own words, every command and flag as `cstudy` has it, and no company names.

## Layout

```text
user-docs/
  getting-started.md     # one page per topic, its slug the file's name
  toolchains.md
  web-ui.md
  ...
```

`user-docs/` sits at the [content root](installation-and-workspaces.md#content-root) beside `problems/`, `tracks/` and `guides/`; the sdist ships it and the wheel ships it as `coding_study/content/user-docs/`. A content root without it has no docs, and `cstudy docs` says so. It holds `<slug>.md` files and nothing else: no folders, no images. A page's slug is its file's name without `.md`: lowercase letters, digits and single hyphens, a letter first, at most 64 characters, as a guide's.

## A page

```markdown
---
title: Check your setup with cstudy doctor
summary: What each row of cstudy doctor checks, and how --fix sets up a workspace.
section: Start here
order: 30
---

# Check your setup with cstudy doctor

`cstudy doctor` checks ...

## The rows
```

### Front matter

The file starts with `---` on its own line, YAML, and `---` again. It is validated by `schemas/user-doc.schema.json`.

| Key | Type | Required | Rules |
|-----|------|----------|-------|
| `title` | string, 1 to 80 characters | yes | The page's `# ` heading repeats it |
| `summary` | string, 1 to 240 characters | yes | One sentence, shown in lists and search |
| `section` | string, 1 to 40 characters | yes | The group the page belongs to in lists, such as `Start here` |
| `order` | integer, 1 or more | yes | The page's place among all pages; no two pages share one |

Pages are listed by `order`. A section is listed where its first page is, and its pages follow one another: no page of another section comes between them.

### Body

| Rule | Detail |
|------|--------|
| Title | The first line after the front matter, and a blank line, is `# <title>` |
| Headings | `##` and `###` split the page into sections. Each heading's id is GitHub's: its text in lower case, without the characters that are not letters, digits, spaces, hyphens or underscores, its spaces turned into hyphens, and `-1`, `-2` added to a repeated one (`## Node.js and pnpm` is `nodejs-and-pnpm`). A deep link names a page and one of these ids |
| Links | To another page, `[the keyboard](web-ui.md#keyboard)`: a page's file name, and an id of its headings after `#`; to a heading of the same page, `[Fix](#fix)`; or to the web, an `https://` address. Nothing else: no link to a spec, an ADR or a file of the repository, since the wheel and the website have none of them |
| Commands | Every `cstudy` command is code: a fenced `bash` block, or inline code. Each one is a command `cstudy` has, with flags it takes ([accuracy](#accuracy)) |
| Keys | Inline code, `Cmd+S`, `Alt+1` |
| Plain Markdown | CommonMark with GitHub's tables: no HTML, which neither the terminal nor the page shows, and no images, which do not ship. A page reads the same in the terminal, the page, GitHub and the website |
| Words | No `TODO` |

## Topics

| Order | Slug | Title | Section |
|------:|------|-------|---------|
| 10 | `getting-started` | Getting started | Start here |
| 20 | `toolchains` | Install the language toolchains | Start here |
| 30 | `doctor` | Check your setup with cstudy doctor | Start here |
| 40 | `workspace` | Your workspace | Start here |
| 50 | `practice` | Work on a problem | Practise |
| 60 | `levels` | Progressive levels and projects | Practise |
| 70 | `service-projects` | Service projects and the dev stack | Practise |
| 80 | `guides` | Guides and learning paths | Practise |
| 90 | `planning` | Plan your practice | Practise |
| 100 | `web-ui` | Practise in your browser | The web UI |
| 110 | `editor` | The editor and code intelligence | The web UI |
| 120 | `settings` | Settings and preferences | Settings and help |
| 130 | `troubleshooting` | Troubleshooting | Settings and help |

The README stays short: what `cstudy` is, the install, the first steps, and a link to these pages. `cstudy` itself links to `toolchains.md` on GitHub from the fixes `cstudy doctor` prints, by the ids of its sections (`#go`), which therefore do not change.

## cstudy docs

```text
cstudy docs [--json]
cstudy docs <topic> [--json]
cstudy docs [<topic>] --open
```

It needs no workspace, except `--open`, which serves the page as `cstudy serve` does.

| Form | Does | Says |
|------|------|------|
| `cstudy docs` | Lists the topics | Each section's name, then its pages, one per line: the slug and the title. Then `read      cstudy docs <topic>` and the web hint. With no `user-docs/`, `no docs in <content root>` |
| `cstudy docs <topic>` | Prints the page, its front matter left out. On a terminal it is Markdown rendered by Rich, which reads without colour too (`--no-color`, `NO_COLOR`); otherwise, piped or redirected, the Markdown text as written | The page, then the web hint |
| `cstudy docs --open`, `cstudy docs <topic> --open` | Finds the topic, then runs `cstudy serve --open` on a free port, whose page opens on the Docs view, or on the topic: the URL adds `&view=/docs` or `&view=/docs/<topic>`. Runs until Ctrl-C | What `cstudy serve --open` prints |

The web hint is one dim line, `Read in the web UI: cstudy docs <topic> --open`, with the topic's slug after a page and `<topic>` after the list. `--json` never prints it.

`--json` of the list prints `{"pages": [...]}`, in order: each page `{"slug", "title", "summary", "section", "order", "headings"}`, where `headings` lists the page's `##` and `###` headings in order, each `{"id", "title", "level"}`, `level` 2 or 3. `--json` of a topic prints the same fields with `"markdown"`, the page as written after its front matter.

| Case | Result |
|------|--------|
| A topic that does not exist | `unknown topic "doctr"; did you mean doctor?`, or `unknown topic "x"; cstudy docs lists the topics`, exit 3 |
| `--open` with `--json` | `--open takes no --json: it serves the page and opens it`, exit 3, and no server starts |
| A page that does not load | What is wrong and which file, exit 5; `cstudy verify --static` names every problem |

## Docs view

The [Docs view](web-ui.md#docs-view) of `cstudy serve` shows the same pages. `Alt+8` and the top bar's `docs` open it.

| Route | Shows |
|-------|-------|
| `#/docs` | The pages by section, each with its title, a link, and its summary, and a search field. The query is kept in the route, `#/docs?search=port` |
| `#/docs/<slug>` | The page, rendered on the server as the web UI renders Markdown, with its code highlighted, in the page's light or dark theme. Beside it, `on this page`, a link to each `##` heading, and every page by section, the open one marked; under it, the previous and the next page |
| `#/docs/<slug>/<id>` | The same page, scrolled to the heading of that id, which takes the focus |

A link between pages, `web-ui.md#keyboard`, goes to `#/docs/web-ui/keyboard`, a link to the same page's heading likewise, and a web link opens elsewhere. Each heading of the page carries the id `doc-<id>`.

The search matches each page's passages: its title with its summary and the text before its first `##`, and each `##` or `###` section with its heading. A passage matches when every word of the query is in it, in any case. The results are in page order, each with the page and the heading, a link to it, and the words around the first match; typing asks the server nothing. `/` focuses the field.

| Method and path | Response |
|-----------------|----------|
| `GET /api/v1/docs` | `cstudy docs --json`, each page with `passages`: `[{"id", "title", "text"}]`, the first with `id` `""`, the page's title, and its summary and opening text; the text is plain, without Markdown's marks |
| `GET /api/v1/docs/{slug}` | `cstudy docs <topic> --json` with `html`, the page as the view shows it, without its `# ` title. An unknown topic: 404 `not_found` with the CLI's message |

## Static checks

`cstudy verify` runs these after the guides' checks, with or without `--static`, when it verifies the whole catalog, as it does the guides' ([guides](guides.md#static-checks)). Each page is one line of its report (`user-docs/doctor.md  static ok`), and a failure fails the run with exit 5.

| Id | Check |
|----|-------|
| D1 | The front matter is there and valid against `schemas/user-doc.schema.json` |
| D2 | `user-docs/` holds only files, each named `<slug>.md` with a valid slug |
| D3 | The body starts with `# <title>` with the title of the front matter; no `TODO`, no HTML tag and no image outside code |
| D4 | No two pages share an `order`, and each section's pages follow one another |
| D5 | Every link is an `https://` address, a page's file name or `#` and an id; the page exists, and so does the heading the id names |
| D6 | Every `cstudy` command in a shell block, a terminal's prompt or fix line, or inline code is a command of `cstudy`, and each of its flags is one the command takes ([accuracy](#accuracy)) |

### Accuracy

A page that names a command `cstudy` does not have, or a flag a command does not take, is wrong, so D6 checks every one against `cstudy`'s own command line, which `cstudy verify` passes it: the commands, their subcommands and the flags of each, `--help` included.

| Where | What is checked |
|-------|-----------------|
| Fenced blocks of `bash`, `sh`, `shell` and `zsh` | Every line |
| Fenced blocks of `text` and `console`, and blocks without a language, which show a terminal's output | A line that starts with the prompt `$ `, and what follows `fix: ` on a line, as `cstudy doctor` prints a fix |
| Inline code | Every span |

In each, the text is split as a shell splits it, and at `&&`, `||`, `|` and `;`; a part that holds the word `cstudy` names the command after it. Global flags (`--workspace PATH`) may come first; the first word that is no flag is the command, and for `cstudy set` and `cstudy config` the next is the subcommand. Each word that starts with `-` is a flag, with any `=value` left out, until `--`; brackets around a word, as in `[--fix]`, are left out. A placeholder in angle brackets as the command (`cstudy <command> --help`) is not checked.

`cli/tests/content/test_user_docs.py` runs D6 over every shipped page against the real command line, so a renamed command or flag fails the fast tests until the pages follow it.

## The website

The website copies these pages; nothing in this repository writes to it.

| It reads | How |
|----------|-----|
| The pages | `user-docs/*.md` of a release tag, `vX.Y.Z`, so the website says what the released `cstudy` does. Each page's URL is its slug |
| The order and the groups | The front matter: `order`, and `section` in the order of each section's first page |
| An index | `cstudy docs --json`, or `uv run cstudy docs --json` in a checkout of the tag: every page with its headings and their ids, in order |
| Links | `<slug>.md#<id>` becomes the website's URL of that page and id; ids are GitHub's, so a website that makes them the same way needs no table |

A page's slug, its headings' ids and its front matter's keys are its interface: renaming one is a change the website must follow, and the release notes say so.
