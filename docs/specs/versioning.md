# Versioning

The code follows [Semantic Versioning](https://semver.org). The version is derived from [Conventional Commits](https://www.conventionalcommits.org) on `main` and is recorded as a git tag. Nothing is published anywhere: no package upload, no GitHub release.

## Commit types and bumps

| Commit | Bump while `0.x` | Bump from `1.0.0` |
|--------|------------------|-------------------|
| `fix:`, `perf:` | patch | patch |
| `feat:` | minor | minor |
| `feat!:`, `fix!:`, or a `BREAKING CHANGE:` footer | minor | major |
| `docs:`, `chore:`, `ci:`, `build:`, `refactor:`, `style:`, `test:` | none | none |

The project is `0.x` (`allow_zero_version`), and a breaking change does not jump to `1.0.0` by itself (`major_on_zero = false`). Release `1.0.0` deliberately, by running the tool with `--major`.

When no commit since the last tag warrants a bump, the workflow does nothing and succeeds.

## What the workflow does

`.github/workflows/version.yml` runs on every push to `main` (and on manual dispatch). When a commit warrants a bump, it:

1. Updates `version` in `pyproject.toml` (the single source of truth) and refreshes the project entry in `uv.lock`.
2. Adds the release to `CHANGELOG.md`.
3. Commits as `github-actions[bot]` with the message `chore(release): vX.Y.Z [skip ci]`.
4. Tags the commit `vX.Y.Z` and pushes the commit and the tag.

It uses `GITHUB_TOKEN`; the bot commit and tag do not start further workflow runs. Expect one bot commit on `main` after a merge that contains a `feat:` or `fix:`.

`cstudy --version` prints the installed version, read from package metadata. The first run on a repository without tags tags the current version, `v0.1.0`, without changing it.

## Configuration

`[tool.semantic_release]` in `pyproject.toml`. Paths in it are relative to the repository root. Preview what the next run would do, from the repository root:

```sh
uv run semantic-release --noop version --print
```

The preview only reports a version on `main`; other branches are not release branches.

## Repository settings

The workflow needs **Settings > Actions > General > Workflow permissions** set to read and write, or the `contents: write` it declares is capped. A rule that blocks direct pushes to `main` also blocks the bot; allow `github-actions[bot]` to bypass it.
