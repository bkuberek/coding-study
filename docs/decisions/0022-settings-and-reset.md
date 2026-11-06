# ADR 0022: Settings edits the whole config file, keeping its comments

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-06 |
| Spec | [cli](../specs/cli.md#configuration), [web-ui](../specs/web-ui.md#settings-view), [progress-and-scheduling](../specs/progress-and-scheduling.md#scheduling-algorithm) |
| Amends | [ADR 0015](0015-local-web-ui.md) (the only file the page writes outside the workspace is the user's own config, on the user's request) |
| Builds on | [ADR 0013](0013-homebrew-distribution.md), [ADR 0015](0015-local-web-ui.md) |

## Context

The owner wants to configure the whole app from the Settings view, including the review intervals. Until now the view edited only the workspace's preferences, `.cs/serve/preferences.json`, a file the page owns and rewrites whole. `config.toml` is the user's: a hand-written file with comments, kept in dotfiles, maybe a link, that `cstudy` only read. Rewriting it from its parsed values would lose all of that.

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

### Two files, one page

Preferences stay per workspace and apply at once; the config stays per user and applies as each key says. The view shows both, under headings that say which is which. They do not merge: a preference is what a page shows, and `cstudy` reads none of them but `code_intelligence` for `doctor`.

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
| Hand-written controls per key | Grows the Settings chunk with every key, against a whole-bundle budget with little headroom, and a new key could be forgotten |
