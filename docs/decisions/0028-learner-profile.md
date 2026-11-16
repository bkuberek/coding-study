# ADR 0028: A learner profile: roles and domains in the config, languages in the workspace

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-16 |
| Spec | [cli](../specs/cli.md#the-learner-profile) (and [`cstudy lang`](../specs/cli.md#cstudy-lang)), [installation-and-workspaces](../specs/installation-and-workspaces.md#workspace-languages), [web-ui](../specs/web-ui.md#filter-component), [guides](../specs/guides.md#metayaml), [content](../specs/content.md#labels) |
| Amends | [ADR 0010](0010-ide-integration.md) (the IDE files cover the workspace's languages only), [ADR 0012](0012-go-and-rust.md) (Go and Rust stay optional only while a workspace has not chosen its languages), [ADR 0020](0020-catalog-labels.md) (guides carry `domains` and `job_roles`; a role profile always keeps `general`), [ADR 0025](0025-concept-guides-and-learning-paths.md) (a guide's metadata gains the two labels) |
| Builds on | [ADR 0008](0008-installable-tool-and-separate-workspaces.md), [ADR 0015](0015-local-web-ui.md), [ADR 0022](0022-settings-and-reset.md), [ADR 0027](0027-compatibility-contract.md) |

## Context

The owner settled the profile on 2026-11-14: a learner profile of languages, job roles and domains, each defaulting to all, is the default filter on every page; a page can widen its filter without changing the profile, and shows a "filtered by your profile" chip while the profile narrows it; the languages also decide which workspace folders exist, with a command to add one; every page uses one standard filter component; all of it is in 1.0. On 2026-11-16 the owner added: languages are added and removed in the terminal and in the page, and the learner chooses whether a removed language's folder stays or goes; the terminal and the page both say, quietly, when the profile hides part of a list. Problems carry `domains` and `job_roles` already ([ADR 0020](0020-catalog-labels.md)); guides carry none.

What exists today:

- A workspace holds every language's practice project: `cstudy init` copies the whole template ([installation-and-workspaces](../specs/installation-and-workspaces.md#cstudy-init)), and `cstudy doctor` fails without Python, Node, pnpm and a JDK, whatever the learner practices.
- The only user-level default filter is `next.tracks` in `config.toml`, read by `cstudy next` and `cstudy mock`.
- The Problems and Guides views each draw their own filter row, and a page's filters reset to nothing on every visit.
- `config.toml` is per user and travels in dotfiles; the marker `.cs/workspace.toml` is per workspace, tracked in the workspace's own repository, and a public surface ([compatibility](../specs/compatibility.md#surfaces)).

Two questions decide the design: where each part of the profile lives, and what happens to the workspaces that exist, which all hold six languages' folders.

## Decision

### Roles and domains are user settings; languages are a workspace fact

| Dimension | Stored in | Key | Default | Why there |
|-----------|-----------|-----|---------|-----------|
| Job roles | `config.toml` | `profile.job_roles` | Every role | Who the learner prepares to be is about the person, like `next.tracks`; it holds in every workspace and outside one (`cstudy list`, `cstudy learn`) |
| Domains | `config.toml` | `profile.domains` | Every domain | The same |
| Languages | `.cs/workspace.toml` | `languages` | Unset: all six | Languages decide which folders, toolchains and IDE files a workspace has, so they must travel with the workspace: a clone on another machine, with another person's config, must still know that it has no `jvm/` |

The page's Settings view shows the three together, under one Profile heading, and says which file holds which. The config keys are drawn by the existing config form ([ADR 0022](0022-settings-and-reset.md)); the languages, which are not a config key, have their own control.

`profile.job_roles` does not offer `general`: an entry for any engineer suits every role, so a narrowed role profile always keeps the entries that list `general`. Without that, a backend profile would hide every data structures and algorithms problem, whose role is `general`.

### Unset languages mean today's workspace

A marker without `languages` is a workspace of all six languages with Go and Rust optional, exactly as before: `cstudy doctor` keeps failing on the four core toolchains and warning on Go and Rust. A marker that lists languages is a choice: the workspace has those folders only, `cstudy doctor` checks those toolchains only, and each chosen language's toolchain is required, Go and Rust included, since the learner asked for them. `cstudy init` without `--lang` writes no `languages`, so a new user's first workspace behaves as today's.

| Workspace | After this change |
|-----------|-------------------|
| An existing one | No `languages` key: unchanged in every way. `cstudy lang list` says all six; `cstudy lang remove` (or editing the marker) narrows it |
| `cstudy init` | The same as before |
| `cstudy init --lang python` | `python/` and the shared folders only, `languages = ["python"]`, a `cstudy doctor` that checks Python and uv and nothing of the other five |

The marker's `schema` stays 1. The key is additive: a 1.0 workspace works with every 1.x, and an older `cstudy` ignores the key and reports the folders a narrowed workspace lacks as missing, which `cstudy doctor --fix` would write, as for any downgrade.

### Removing a language keeps its folder unless the learner deletes it

`cstudy lang remove` takes a language out of the list and keeps its folder: practice files are the learner's, and the folder only stops being checked, generated for and offered. `--delete-folder` also deletes the language's folder, after a question that `--yes` answers and that a script without `--yes` cannot skip (exit 3, as `cstudy reset`). The Settings view offers the same choice, keep or delete, and a delete needs a second confirmation that shows what goes. Progress, `.archive/`, `projects/` and `notes/` stay either way.

| Rule | Why |
|------|-----|
| The delete is refused while an attempt in the language is in progress | Its files are in the folder; `cstudy done` and `cstudy abort` already end an attempt, so no `--force` is needed |
| `jvm/` goes only when neither Java nor Kotlin remains | One Gradle build holds both subprojects |
| The last language cannot be removed (exit 3) | A workspace with no language has nothing to start |
| `--delete-folder` on a language already removed deletes the folder that stayed | The learner who kept a folder can delete it later the same way, and a delete interrupted halfway finishes by running the command again |

### One filtering rule, in the domain, for the terminal and the page

A pure domain module holds the profile and the rule that matches an entry against it, and every surface calls it: `cstudy list`, `cstudy next`, `cstudy mock` and `cstudy learn`, and through them the Problems view, its Next card, the Mock view and the Guides view. The web UI's [parity rule](../specs/web-ui.md#principles) then holds by construction: the command above a view, run in a terminal, shows the same rows.

| Rule | Detail |
|------|--------|
| A dimension | Matches an entry that lists any of the profile's values. A narrowed role profile also keeps `general` |
| Entries without the dimension | Kept: a rubric problem has no language, a problem of your own may list no labels, and the profile never hides them |
| An explicit filter | `--lang`, `--domain` or `--role` replaces the profile in its dimension, and may name a value outside it |
| Widening | `--widen lang\|role\|domain\|all` drops the profile in that dimension without editing it; the page's filters do the same per view, and its route keeps it |
| Where it applies | Lists to choose from: problems, the next pick, mock picks, guides and paths. Not a set (your own list), progress and reviews (what you did), the docs, `cstudy verify` or a command given a slug |

The CLI applies the profile by default, as the page does; `--widen` drops it for one run.

### The profile says what it hides

While the profile hides at least one entry, the terminal's output ends with one dim line on standard output, `filtered by your profile: 120 of 400 problems · languages python, go · --widen all shows all 400`, and the page's filter row opens with a chip in the ordinary chip style, `120 of 400 · your profile: python, go ×`, a button that widens, followed by `edit profile`. `--json` carries the count as `profile.hidden`, never as text. A profile that narrows but hides nothing shows neither. The line goes to standard output with the output it describes, as the web hints of `cstudy learn` and `cstudy docs` do; standard error stays for errors, warnings and debug notices.

### Languages bound what can start

A workspace's languages are the only ones a new attempt can start in, since the other folders may not exist: `cstudy start` refuses another language with exit 3 and the `cstudy lang add` to run, and `cstudy next` and `cstudy mock` pick only problems a workspace language can start. A service project, which runs in Docker and uses no language folder, is filtered by its language as a preference but starts in any workspace. `default_lang` applies while it is one of the workspace's languages; otherwise the first of them, in `cstudy`'s language order, is the default.

### One filter component

The page's filter row is one module, used by every view that filters: its search, its lists, the More menu, the chips, the count, Clear, and the profile's options and chip. Each view declares its dimensions and their choices; the component draws them, keeps them in the route and names the CLI command. The Problems and Guides views move onto it; the Mock view uses its profile chip.

### Guides carry the labels too

A guide's `meta.yaml` gains `domains` and `job_roles` from the closed lists of [content](../specs/content.md#labels), required for every catalog guide. A path matches a filter when any of its steps does. `cstudy verify` checks them through the guide schema (G1) and warns (G12) when a guide shares no domain with the problems it links.

## Consequences

- A learner who practices one language installs one toolchain and gets a clean `cstudy doctor`.
- Removing a language can delete practice files when the learner asks for it; the question, the second confirmation in the page and the refusal while an attempt is open are the guards.
- Two stores hold one profile. The Settings view hides the split behind one heading; the terminal edits roles and domains with `cstudy config edit` and languages with `cstudy lang`.
- `cstudy list`, `next`, `mock` and `learn` print fewer rows once a profile narrows, and say so in one dim line with the counts and the flag that widens. Their `--json` documents gain a `profile` field that says which values narrowed and how many entries they hid; nothing else in them changes.
- The IDE files, the doctor rows and the `doctor --fix` steps branch on the workspace's languages; the language tables keep their exhaustive `match`.
- Every one of the 132 guides needs two labels before the schema requires them.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| The whole profile in `config.toml` | Languages decide folders, which are per workspace: a second workspace, or a clone on a machine with another config, would disagree with its own folders, and `cstudy doctor --fix` would recreate folders the learner had chosen not to have |
| The whole profile in the marker | Roles and domains would need a new command to edit, would be lost outside a workspace (`cstudy list` and `cstudy learn` run without one), and would differ per workspace for the same person |
| A profile file of its own (`.cs/profile.toml` or `~/.config/coding-study/profile.toml`) | A third store beside the config and the marker, with its own parser, contract snapshot and Settings save path, for three keys |
| Writing all six languages into every new marker | Turns Go and Rust into required toolchains for every new workspace, against [ADR 0012](0012-go-and-rust.md), and makes "unset" and "all" mean the same while the doctor rule needs them apart |
| A page-only profile | Breaks the parity rule: the command above a view would not show its rows |
| Exact matching of `general` | Hides the algorithms catalog from every narrowed role profile |
| Deleting the folder on every removal | Deletes practice files the learner may want back; keeping is the default and deleting is a choice |
| Never deleting the folder | Leaves the learner to find each language's folders by hand (`go.work` beside `go/`, `jvm/` shared by two languages) |
| A `--force` past an attempt in progress | Would delete the files of an attempt the progress database still calls open; `cstudy abort` ends it first in one command |
| The profile line on standard error | It describes the output it ends and belongs with it when paged or saved; the existing dim hints are on standard output |
