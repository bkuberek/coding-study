# Spec: Installation and Workspaces

`cstudy` is a tool you install, and you practice in a **workspace**: a directory of your own, versioned in its own git repository if you want, that holds your solutions, notes and progress. The tool ships the **content** (problems, tracks, runners, schemas and the workspace templates), so this repository never doubles as a workspace and solutions are never committed to it by accident ([ADR 0008](../decisions/0008-installable-tool-and-separate-workspaces.md)).

## Install

```bash
uv tool install git+https://github.com/bkuberek/coding-study
pipx install git+https://github.com/bkuberek/coding-study
```

Both build the project at the repository root. A content author works from a checkout instead: `uv run cstudy ...` in the checkout, or `uv tool install --editable .` to put that checkout's `cstudy` on `PATH`.

| Item | Rule |
|------|------|
| Distribution | `coding-study`, defined by the root `pyproject.toml` (hatchling); the `cstudy` script |
| Wheel | `coding_study/` from `cli/src/coding_study/`, plus `coding_study/content/{problems,tracks,runners,schemas}` from the repository root |
| sdist | The same top-level paths as the checkout (`cli/src`, `problems`, `tracks`, `runners`, `schemas`), so a wheel built from the sdist equals one built from the checkout |
| Excluded | Build output and caches (`node_modules`, `build`, `.gradle`, `.kotlin`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`) and `runners/python/tests` |
| Workspace templates | Package data in `coding_study/adapters/workspace_template/`: the three practice projects with the Gradle wrapper and lock files |

## Content root

The content root holds `problems/`, `tracks/`, `runners/` and `schemas/`. `cstudy` reads it and never writes to it, except `cstudy new` in a checkout.

| Order | Source | Used for |
|-------|--------|----------|
| 1 | `--content PATH` (global flag) | An author verifying a checkout with an installed `cstudy` |
| 2 | `CSTUDY_CONTENT` | Same, from the environment |
| 3 | The bundled copy (`coding_study/content/`) | Any installed `cstudy` |
| 4 | The source checkout `cstudy` runs from (`cli/src/coding_study` two levels below a directory with `problems/` and `schemas/`) | `uv run cstudy` and editable installs in a checkout |

A root given by flag or variable must contain `problems/` and `schemas/`, or the command exits 3. A checkout found by rule 1, 2 or 4 is **editable**: `cstudy new` writes into it. The bundled copy is read-only.

## Workspace root

| Order | Source |
|-------|--------|
| 1 | `--workspace PATH` (global flag) |
| 2 | `CSTUDY_WORKSPACE` |
| 3 | The nearest directory, from the current one upward, that holds `.cs/workspace.toml` |
| 4 | The current directory |

The marker `.cs/workspace.toml` makes a directory a workspace. Every command that needs one (all but `cstudy init`, `cstudy doctor`, `cstudy list` and `cstudy show`) exits 3 when the resolved directory has no marker: `no coding-study workspace at <dir> (no .cs/workspace.toml): run cstudy init`. Outside a workspace, `cstudy list` and `cstudy show` read the catalog with empty progress and keep their caches in `$XDG_CACHE_HOME/coding-study/catalog/` (default `~/.cache/coding-study/catalog/`); `cstudy doctor` checks the toolchains only.

### Marker

```toml
# coding-study workspace (docs/specs/installation-and-workspaces.md); keep it in version control.
schema = 1
created_with = "0.1.0"
```

| Key | Meaning |
|-----|---------|
| `schema` | Workspace layout version; this `cstudy` supports `1`. A newer schema fails `cstudy doctor` (upgrade `cstudy`) and every command that needs a workspace exits 3 |
| `created_with` | The `cstudy` version that ran `cstudy init`; `cstudy doctor` prints it next to the running version |

### Layout

```text
<workspace>/
  .cs/workspace.toml      # marker (tracked)
  .cs/runtime/            # materialized runners (ignored, per machine)
  .cs/                    # index, cases, calibration, build, runs caches (ignored)
  .gitignore, README.md
  python/                 # pyproject.toml (dev tools: pyright, ruff, debugpy), uv.lock, practice/<snake_slug>.py
  typescript/             # package.json, pnpm-lock.yaml, tsconfig.json, support.ts, practice/<slug>.ts
  jvm/                    # Gradle wrapper, settings.gradle.kts, java/ and kotlin/ subprojects
  notes/                  # answers to non-autograded items
  problems/               # your own problems, overlaid on the catalog
  .archive/               # previous attempts (tracked)
  .statements/            # rendered statements (ignored)
  progress.db             # SQLite, created on first use (ignored; cstudy export backs it up)
```

Every path `cstudy` prints for a workspace file is relative to the workspace root (`python/practice/two_sum.py`, `.statements/two-sum.md`). `progress_db` in the config file is relative to it too.

## cstudy init

```text
cstudy init [PATH] [--git] [--force]
```

Creates a workspace in `PATH` (default: `--workspace`, then `CSTUDY_WORKSPACE`, then the current directory), creating the directory when needed.

| Step | Rule |
|------|------|
| Refusals (exit 3) | `PATH` already holds a marker (`cstudy doctor --fix` repairs a workspace); `PATH` is inside another workspace; `PATH` is at or below a content checkout (a directory with `problems/` and `schemas/`) unless `--force` |
| Files | Copies the template: the three practice projects, `notes/` and `problems/` (each with `.gitkeep`), `README.md` and `.gitignore`; makes `jvm/gradlew` executable; writes the marker. An existing file is never overwritten, so `cstudy init` can adopt a directory that already has files (for example a cloned repository) |
| Runtime | Materializes the runners into `.cs/runtime/` ([below](#runner-runtime)), so an IDE can import the projects right away |
| `--git` | Runs `git init` in `PATH`; `cstudy` never commits |
| Output | `created workspace <path>`, the number of files written and skipped, then the next steps: `cd <path>`, `cstudy doctor --fix`, `cstudy start two-sum` |

`cstudy init` installs nothing: `cstudy doctor --fix` runs `uv sync`, `pnpm install` and the Gradle warm-up.

The workspace `.gitignore` ignores `/.cs/*` except `/.cs/workspace.toml`, `/.statements/`, `progress.db*`, `node_modules/`, `.venv/`, `build/`, `.gradle/`, `.kotlin/`, `__pycache__/` and `.ruff_cache/`. Practice files, notes, `.archive/` and your problems stay tracked, and you commit them when you choose ([PRD Q3](../prd.md#8-open-questions)).

## Runner runtime

The practice projects build and run against the runners, and Gradle, uv and Node write next to what they build. The bundled runners live in the installed package, which must stay read-only, so each workspace gets its own copy:

| Item | Rule |
|------|------|
| Location | `.cs/runtime/runners/{python,typescript,jvm}`: the content root's `runners/<name>/` without `tests/` and build output |
| Stamp | `.cs/runtime/stamp.json`: a SHA-256 over the relative path and bytes of every copied source file |
| Refresh | Before the first runner prepares in a command, and in `cstudy doctor`, `cstudy doctor --fix` and `cstudy init`: when the stamp differs from the content's digest, changed files are rewritten, removed files deleted, unchanged files keep their timestamps, and build output (`build/`, `.gradle/`, `node_modules/`, `.kotlin/`, `__pycache__/`) stays |
| Wiring | Relative paths in the tracked project files: `python/pyproject.toml` depends on `../.cs/runtime/runners/python` (editable), `typescript/support.ts` re-exports `../.cs/runtime/runners/typescript/support.ts`, `jvm/settings.gradle.kts` includes `../.cs/runtime/runners/jvm`, and the reference build in `.cs/build/jvm` includes `../../runtime/runners/jvm` |

Because the wiring is relative, a workspace keeps working when it moves or is cloned on another machine; there `cstudy doctor --fix` recreates `.cs/runtime/`, the venv, `node_modules` and the Gradle build. Editors open `python/` (pyright and ruff find `.venv`), `typescript/` (tsserver finds `node_modules`) and `jvm/` (IntelliJ imports it as one Gradle project).

## cstudy doctor in a workspace

| Check | `ok` | Otherwise |
|-------|------|-----------|
| `content` | Path, `bundled` or `checkout` | FAIL when the content root cannot be found |
| `workspace` | Path and `created with cstudy <version>` (with the running version when it differs) | WARN when there is no workspace (`fix: cstudy init`); FAIL for an unreadable marker or a newer schema |
| `workspace files` | Every template file exists | FAIL listing up to 5 missing files, `fix: cstudy doctor --fix` |
| `runner runtime` | The stamp matches the content | FAIL when missing or stale, `fix: cstudy doctor --fix` |
| `jvm/gradlew`, `python/.venv`, `python debugpy`, `typescript/node_modules` and `runner <lang>` | As in [cli](cli.md#cstudy-doctor) | As in [cli](cli.md#cstudy-doctor) |

`cstudy doctor --fix` first writes every missing template file (never overwriting one, so practice files are never touched), refreshes the runner runtime, then runs `uv sync` in `python/`, `pnpm install` in `typescript/` (and in the content checkout's `runners/typescript` when the content is a checkout), and the Gradle warm-up in `jvm/`. Outside a workspace it exits 3.

## Your own problems

`<workspace>/problems/` uses the [problem format](problem-format.md) and is overlaid on the content root's `problems/`:

| Rule | Behavior |
|------|----------|
| Catalog | The union, in directory name (id) order; `cstudy list`, `cstudy next`, `cstudy start`, `cstudy test` and `cstudy verify` treat both alike |
| Slug collision | The workspace problem wins and hides the content problem with that slug entirely (no file-level merge). Your practice files and progress therefore always match the problem you wrote, also after an upgrade adds a problem with your slug |
| Id collision | Ids only order and name directories; two problems with the same id and different slugs are both listed, and `cstudy verify` reports the duplicate id (S2) |
| `cstudy new` | With bundled content it writes `problems/<id>-<slug>/` in the workspace, numbering from `5001` above the workspace's highest id, so new catalog problems never take your ids; with an editable checkout it writes into the checkout as before (highest checkout id plus one) |
| Tracks | Non-autograded items come from the content root only |

## Developing coding-study

The checkout is content, not a workspace:

- `cstudy init` inside it refuses without `--force`; as a second guard the root `.gitignore` ignores `.cs/`, `.statements/`, `progress.db*` and `progress-export.json` anywhere, and `/workspace/`, `/workspaces/`, `/ws/`, `/python/`, `/typescript/`, `/jvm/`, `/notes/` and `/.archive/` at the root.
- Point `CSTUDY_WORKSPACE` (or `--workspace`) at a workspace outside the checkout; `uv run cstudy verify` then reads the checkout's content and builds with that workspace's toolchains.
- The CLI tests never use a workspace in the checkout: fixtures create temporary workspaces, and the slow tests set one up per session with `cstudy init` and the `cstudy doctor --fix` steps.

## Replaces

`CS_ROOT` and the repository-root search (`problems/` and `schemas/` above the current directory) are gone: `CSTUDY_CONTENT` or `--content` picks content, and `CSTUDY_WORKSPACE` or `--workspace` picks the workspace.
