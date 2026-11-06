# ADR 0022: Settings edits the whole config file, keeping its comments, and can reset progress

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-06 |
| Spec | [cli](../specs/cli.md#configuration) (and [`cstudy reset`](../specs/cli.md#cstudy-reset)), [web-ui](../specs/web-ui.md#settings-view), [progress-and-scheduling](../specs/progress-and-scheduling.md#scheduling-algorithm), [installation-and-workspaces](../specs/installation-and-workspaces.md#what-cstudy-reset-deletes) |
| Amends | [ADR 0015](0015-local-web-ui.md) (the only file the page writes outside the workspace is the user's own config, on the user's request) |
| Builds on | [ADR 0013](0013-homebrew-distribution.md), [ADR 0015](0015-local-web-ui.md) |

## Context

The owner wants to configure the whole app from the Settings view, including the review intervals, and to be able to start over: "ask for confirmation, and say it can't be undone". Until now the view edited only the workspace's preferences, `.cs/serve/preferences.json`, a file the page owns and rewrites whole. `config.toml` is the user's: a hand-written file with comments, kept in dotfiles, maybe a link, that `cstudy` only read. Rewriting it from its parsed values would lose all of that.

## Decision

### One place describes a key

`adapters/toml_config.py`, which parses the file, holds every key once: its name, kind, allowed values, default, help, when a change applies, and the converter the parser reads it with. `GET /api/v1/config` serves that description with each key's value, and the Settings chunk draws its controls from it alone, so a new key needs no front-end change. A test holds the description equal to the keys the parser reads. `done.auto_commit`, reserved, shows disabled and says so; a write to it is refused.

### tomlkit writes the file

`adapters/toml_config_file.py` changes only the keys that differ from those in force, with tomlkit, a pure-Python library whose parse and dump give the same text back. Comments, formatting and keys this `cstudy` does not know all stay.

| Rule | Detail |
|------|--------|
| Validation | The parser's own: the new document goes through `config_issues`, and an issue the change adds refuses the whole change with the CLI's wording, 422 `usage`. An issue the file already had stays the user's to fix, so fixing one bad value of two is allowed |
| A file that does not parse | Refused and never overwritten: 503 `environment`, with the parser's message. The form shows the message and its Save is disabled; `cstudy config edit` opens the file |
| Atomic | A new file beside the real one, then a rename, keeping its mode; a link stays a link, since the real file is what gets replaced |
| Reach | The file is found as every command finds it, `CSTUDY_CONFIG` included, and it is made, with its folder, by the first change that needs it |
| Import cost | Only the web server imports the module, so no other command loads tomlkit (NFR-2) |

### The dependency reaches every install

tomlkit is a runtime dependency in `pyproject.toml`, so `uv.lock` pins it. The release builds its hashed `requirements.txt` from the lock with `uv export`, and the Homebrew formula installs that file with `--require-hashes --only-binary=:all:`. tomlkit publishes a `py3-none-any` wheel, so that install needs no build and no new formula step. `uv tool install` and pipx resolve it from the wheel's metadata.

### `progress_db` moves nothing

A new path changes where `cstudy` looks, not where the data is. The page asks first, with the API's `confirm`, naming whether a database exists at the new path, and the terminal says the same after the edit, since a file open in an editor can't ask before it saves. No code moves, copies or deletes a database for this.

### Two files, one page

Preferences stay per workspace and apply at once; the config stays per user and applies as each key says. The view shows both, under headings that say which is which. They do not merge: a preference is what a page shows, and `cstudy` reads none of them but `code_intelligence` for `doctor`.

### A reset goes by what a path holds

`cstudy reset` and the Danger section call one use case. What you practised goes, and what `cstudy doctor --fix` would have to install again stays. Progress is the default; your code is an option, off by default, and `.archive/` a third, since keeping earlier attempts while deleting the current ones is a thing a person may want.

| Rule | Detail |
|------|--------|
| A word, not a flag | The CLI asks for the word and the API needs it in the body, so a plain POST can't reset, and no stray click or replayed request can. A shell with no terminal must say `--yes` |
| Nothing goes until every check passed | The word, then nothing running, then each target resolved inside the workspace root, links on the way and links within included. A link that leaves refuses the whole reset, and the user removes it: a reset is no time to guess |
| One transaction | The rows go in one `DELETE` per table inside a single transaction, keeping the file, its schema and write-ahead log as they are. A failure changes nothing |
| Ids keep rising | SQLite would give the next attempt id 1 again, and a kept `.archive/two-sum/1-python/` would then be overwritten by the next attempt 1. `meta` records the highest id deleted, and a new attempt's id goes above it, which needs no migration |
| Running work | The server's own runs and jobs block it, with their slots held so none starts during the reset. Runs of the terminal are seen by their runner's command line, which names `.cs/runs/`: a reset is too rare to make every run hold a lock for it |

## Consequences

- One more runtime dependency, about 80 KB, loaded only by `cstudy serve`.
- The first time a value is written, tomlkit decides the placement of a new key or table: a new key joins the end of its table, a new table goes at the end of the file.
- The page's security model gains one write route under the same checks: Host, cookie, Origin, CSRF. It can change the user's `progress_db`, so it asks first.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| `tomli-w`, writing the parsed values back | Loses every comment and all formatting: the file stops being the user's |
| Editing lines with regular expressions | Breaks on inline tables, dotted keys and multi-line values, which are all valid and which this code would then have to parse anyway |
| A small writer of our own that keeps comments | Reimplements a TOML parser that keeps trivia, for no saving: tomlkit is about 80 KB and pure Python |
| Leaving the config to `cstudy config edit` | The owner asked for one page that configures the app |
| A reset that replaces `progress.db` with a new file | A second process with the old file open would go on writing to a deleted file, and the write-ahead log files would need care. Deleting rows in a transaction has neither problem |
| `"confirm": true` for a reset, as the page's other questions | A boolean is what a careless script sends. The owner asked for the word |
| A lock every run holds, for a reset to test | Touches every command that runs code, for an action a user takes rarely and by hand |
| Hand-written controls per key | Grows the Settings chunk with every key, against a whole-bundle budget with little headroom, and a new key could be forgotten |
