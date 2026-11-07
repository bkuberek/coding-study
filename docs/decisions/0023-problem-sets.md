# ADR 0023: Problem sets are a file in the workspace, and the terminal and the page study from them

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-06 |
| Spec | [cli](../specs/cli.md#cstudy-set) ([`cstudy list`](../specs/cli.md#cstudy-list), [`cstudy next`](../specs/cli.md#cstudy-next), [`cstudy reset`](../specs/cli.md#cstudy-reset)), [progress-and-scheduling](../specs/progress-and-scheduling.md#cstudy-next-selection), [web-ui](../specs/web-ui.md#sets-view), [installation-and-workspaces](../specs/installation-and-workspaces.md#layout) |
| Amends | [PRD](../prd.md): FR-17 joins, and NFR-12's whole-bundle budget rises. [ADR 0015](0015-local-web-ui.md): the page writes one more file of the user's, `sets.yaml`, through routes of its own |
| Builds on | [ADR 0015](0015-local-web-ui.md), [ADR 0020](0020-catalog-labels.md), [ADR 0022](0022-settings-and-reset.md) |

## Context

The owner: "this makes it easy to create a set of problems to study and not have to look for them". Someone with an interview coming up wants to name a list, put problems in it, and be told what to do next from that list. Filters can't express a hand-picked list: they select by what a problem is, not by what you chose. A problem can be in more than one set.

## Decision

### A set is one file in the workspace

A set is a name, an optional description and an ordered list of slugs, of problems and items alike. They live in `sets.yaml` at the workspace root, which `cstudy` makes at the first write and the template does not ship:

```yaml
sets:
  backend-loop:
    description: The backend loop on the 12th
    problems:
      - two-sum
      - url-shortener
```

It is tracked, as practice files are, so it can be read, edited by hand, committed and copied to another workspace. It is not in `progress.db`, because a set is what you plan to do and the database is what you did. So [`cstudy reset`](../specs/cli.md#cstudy-reset) keeps it, with `--files` and with `--archive`, and its preview says so; and `cstudy doctor --fix`, which writes only the template files a workspace lacks, leaves it alone.

| Rule | Detail |
|------|--------|
| Name | A kebab-case slug: a lowercase letter first, then lowercase letters, digits and single hyphens, at most 64 characters. Anything else is refused and says what to use. Creating a name that exists is an error, never a merge |
| Order | Insertion order, in the file as in every view. `cstudy set move <name> <slug> <position>` reorders, and so do the page's Up and Down buttons |
| A slug not in the catalog | `add` refuses it and suggests the nearest slugs, and nothing is added. One that vanishes later, or that a hand edit brought in, shows as `missing`, fails no command, counts in no total and can still be removed |
| A slug already there | `add` does nothing and says so; `remove` of a slug that is not there does the same |
| A file that does not parse | Every command that reads it says what is wrong and which file, exit 4, 503 `environment` on the page, and nothing overwrites it. Commands that have no `--set` never read it, so a broken file does not stop `cstudy next` or the Problems view |

### What a write keeps

`sets.yaml` is the user's, so a write changes only the lines it must. There is no comment-keeping YAML library among the dependencies, and PyYAML's dump loses every comment, so the writer takes the positions PyYAML reports when it composes the file and edits the text at those positions:

| Change | What it touches |
|--------|-----------------|
| Add, remove or move a slug | The lines of that slug. A comment above a slug, or at the end of its line, goes with the slug |
| Create | New lines after the last set |
| Rename | The name in its line |
| Delete | The set's lines and the comment directly above it |

Everything else stays byte for byte: comments, blank lines, quoting and the order of sets and keys. A list in flow style (`problems: [a, b]`) becomes a block list when it changes, and a comment inside the brackets goes with it; a set written whole in flow style, or with no `problems` key, is written again in the canonical form when it changes, losing the comments inside that set alone.

The writer parses what it would write and compares it with what it meant to write. When they differ, as they do for a change to a list that a YAML alias shares, it refuses, writes nothing and says to edit the file by hand.

The write is atomic, by `Workspace.write_within`: a new file beside the old one, then a rename, keeping the mode. It refuses a `sets.yaml` that is a symbolic link, as the page's file API refuses one. Changes take a lock, `.cs/sets.lock`, for the read and the write together, so a change from the terminal and one from the page never lose each other's work.

### `cstudy set`, and `--set`

`cstudy set` is a group: `list`, `show`, `create`, `add`, `remove`, `move`, `rename` and `delete`, with `--json` on `list` and `show`. No command or option was named `set` before. `cstudy list --set <name>` and `cstudy next --set <name>` take a set wherever the other filters go, and combine with them by AND.

`cstudy list --set` lists the set's rows in the set's order, problems and items together, not problems then items as the plain list does, and adds `set` to its document with the slugs that are missing. It needs a workspace, though `cstudy list` alone does not, since the file is in one.

### `next --set` goes in the order you chose

Within a set the order is the plan, so the weakness score does not choose. `next --set` resumes an attempt in progress in the set, then takes the first entry in the set's order that isn't passed, then a due review from the set. When there is nothing left it says the set is finished.

| Rule | Detail |
|------|--------|
| Weakness | Unchanged. A due review is ranked by the same priority as ever, and the score is computed over the same scope as without `--set`, so a set never changes how weak a group reads |
| Passed | At least one attempt that passed, whatever the review schedule says now, so a problem that has fallen due still counts as passed |
| Every track | `--set` needs no `--track`: a set may hold items the configured `next.tracks` leaves out. `--track` still narrows it |
| Drafts | A problem of your own marked `draft` that you put in a set stays in it. `cstudy next` alone offers only `ready` content, but a hand-picked list means what it says, and `cstudy start` takes a draft |
| `--new` and `--review` | `--new` skips the resume and the review; `--review` takes only a due review |
| The JSON | `cstudy next --json` stays additive: `pick` keeps its three values, the entry in the set's order being `new`, and the document gains `set` only under `--set` |

### The page has one view more

Sets is a view in the top navigation, second after Problems because it answers the same question, what to study; the views after it each move one number along. Its code and its styles are a chunk of their own. The Problems view gains a Set filter, its Next card follows the filter, and its rows and the Problem view gain a control that shows which sets a problem is in and adds or removes it.

The routes are under `/api/v1/sets`. Each write is behind the same checks as the page's other writes (Host, cookie, `Origin`, CSRF) and does what the matching `cstudy set` command does through the same use case, with the same refusals.

### The budget rises

The owner approved it on 2026-11-06: "just raise the budget". NFR-12's whole bundle goes from 350 KB to 400 KB gzip and from 1,024 KB to 1,200 KB raw. The bundle was at 349.5 KB gzip before this work, so no new view could have shipped under the old figure. The budget before a file is editable stays at 600 KB raw, because that is what the user waits for, and the Sets view adds nothing to it.

## Consequences

- A set's progress is computed each time from `progress.db` and is never stored, so `sets.yaml` stays a plain list and a reset leaves it true.
- A problem that fails stays the next pick until it passes or the user moves it, since the order is the user's. `cstudy set move` is the way past one.
- The writer knows more about YAML's layout than a dump would. Its failure is a refusal, not a damaged file, because it checks what it would write first.
- The Problems view reads one more document, and a `sets.yaml` that does not parse shows as an error beside its filter, without stopping the view.

## Later options

Not built, and each can be added without changing the file's shape:

| Option | What it would add |
|--------|-------------------|
| Sets shipped in the catalog | Curated sets under the content root, copied into `sets.yaml` by choice |
| Sharing beyond copying the file | A way to import a set from a file or a link |
| A language per set | `cstudy next --set` starting in that language |
| Due dates | A date on a set, and a countdown in the Sets view |

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Sets as tables in `progress.db` | `cstudy reset` would have to spare them, the file could not be read or committed, and a set is not a record of what you did |
| A tag on each problem | A tag has no order, and catalog files are not the user's to edit |
| `yaml.safe_dump` of the whole file | Every comment gone at the first `cstudy set add`, which is why ADR 0022 turned down the same thing for `config.toml` |
| `ruamel.yaml`, which keeps comments | A second YAML dependency for one small file, where the positions PyYAML already reports are enough |
| A `format` key in the file | Nothing reads it yet; a key can be added when one does, since a file without it is then format 1 |
| `add --at` to reorder | `add` of a slug already there does nothing, so it could not move one; `move` says what it does |
| Weakness choosing within a set | The order is the point of a hand-picked list |
| Counting a missing slug in the total | A set could never finish once the catalog dropped a slug |
