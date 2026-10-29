# Versioning

The code follows [Semantic Versioning](https://semver.org). The version is derived from [Conventional Commits](https://www.conventionalcommits.org) on `main` and is recorded as a git tag. Each release is published as a GitHub release that holds the wheel and a hashed requirements file, and as the `cstudy` formula in the Homebrew tap [`bkuberek/homebrew-tap`](https://github.com/bkuberek/homebrew-tap) ([ADR 0013](../decisions/0013-homebrew-distribution.md)). Nothing is uploaded to PyPI.

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

`.github/workflows/version.yml` runs on every push to `main` (and on manual dispatch). Its three jobs run in order, each after the one before succeeds:

| Job | Runs | Does |
|-----|------|------|
| `version` | Always | Bumps the version, commits and tags, when a commit warrants it |
| `release` | When `version` tagged a release on `main`, or on a manual run on `main` | Attaches the release files to the GitHub release ([GitHub release](#github-release)) |
| `homebrew` | After `release` | Points the tap's formula at those files ([Homebrew tap](#homebrew-tap)) |

When a commit warrants a bump, `version`:

1. Updates `version` in `pyproject.toml` (the single source of truth) and refreshes the project entry in `uv.lock`.
2. Adds the release to `CHANGELOG.md`.
3. Commits as `github-actions[bot]` with the message `chore(release): vX.Y.Z [skip ci]`.
4. Tags the commit `vX.Y.Z` and pushes the commit and the tag.

It uses `GITHUB_TOKEN`; the bot commit and tag do not start further workflow runs, which is why publishing is a job of this workflow and not a workflow triggered by the tag. Expect one bot commit on `main` after a merge that contains a `feat:` or `fix:`.

`cstudy --version` prints the installed version, read from package metadata. The first run on a repository without tags tags the current version, `v0.1.0`, without changing it.

## GitHub release

The `release` job builds the release files from a checkout of the tag, with the tooling in `packaging/` of the commit the run is for (the tag may predate a change to it):

| File | Made with | Content |
|------|-----------|---------|
| `coding_study-X.Y.Z-py3-none-any.whl` | `uv build --wheel` | The `cstudy` package with its bundled content ([install](installation-and-workspaces.md#install)) |
| `requirements.txt` | `uv export --locked --no-dev --no-emit-project --no-header --format requirements.txt` | Every runtime dependency at its `uv.lock` version, with the sha256 of each of its published files |

It creates the GitHub release `vX.Y.Z` with `GITHUB_TOKEN`, titled with the tag, with the tag's `CHANGELOG.md` section as its notes (`packaging/release_notes.py`). A release that already has both files is left unchanged; one that lacks a file gets both files built and uploaded again.

## Homebrew tap

The `homebrew` job downloads the two files from the GitHub release, so the formula hashes exactly what the release serves. It renders `packaging/homebrew/cstudy.rb.template` with their URLs and sha256 (`packaging/homebrew/render_formula.py`) and commits the result as `Formula/cstudy.rb` to `main` of `bkuberek/homebrew-tap`, as `github-actions[bot]`, with the message `cstudy X.Y.Z`. An unchanged formula is not committed. Users get the release with `brew upgrade cstudy`.

| Formula step | What it does |
|--------------|--------------|
| `depends_on "python@3.13"` | Runs `cstudy` on Homebrew's Python 3.13, in a virtual environment in the keg's `libexec` |
| `resource "requirements"` | `pip install --require-hashes --only-binary=:all: --no-deps`: binary wheels from PyPI, each checked against its hash, so installing needs network access. Homebrew's own `std_pip_args` build from source, and rpds-py and watchfiles need Rust for that |
| `url` | `pip install` of the release wheel; `cstudy` is linked into Homebrew's `bin` |
| `preserve_rpath` | Keeps the `@rpath` install name of watchfiles' prebuilt extension, which has no header room for Homebrew's absolute one |
| `test` | `cstudy --version` prints the formula's version, and `cstudy init` creates a workspace |

Change the formula in the template, never in the tap: the next publish overwrites the tap's copy. Before merging a template change, install it from a local build through a throwaway tap, from the repository root:

```sh
uv build --wheel --out-dir /tmp/cstudy-dist
uv export --locked --no-dev --no-emit-project --no-header --format requirements.txt --output-file /tmp/cstudy-dist/requirements.txt
brew tap-new --no-git bkuberek/cstudy-local
python3 packaging/homebrew/render_formula.py --base-url file:///tmp/cstudy-dist \
  --wheel /tmp/cstudy-dist/coding_study-*-py3-none-any.whl --requirements /tmp/cstudy-dist/requirements.txt \
  --output "$(brew --repository bkuberek/cstudy-local)/Formula/cstudy.rb"
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --formula bkuberek/cstudy-local/cstudy
brew test bkuberek/cstudy-local/cstudy
brew audit --strict --formula bkuberek/cstudy-local/cstudy
HOMEBREW_NO_AUTOREMOVE=1 brew uninstall --formula cstudy
brew untap bkuberek/cstudy-local
```

`HOMEBREW_NO_AUTOREMOVE=1` keeps `brew uninstall` from also removing every other formula that was installed only as a dependency and that nothing needs any more; uninstall `python@3.13` yourself if you installed it only for this check.

## Publishing again

A manual run on `main` publishes the newest tag reachable from `main`, skipping the steps already done, so it repairs a publish that failed or never ran:

```sh
gh workflow run version.yml --ref main
```

Like a push, the run first cuts a release when an unreleased commit warrants one, and then publishes that release. To replace the files of a published release, delete them from the GitHub release first; the next manual run builds and uploads them again and updates the formula. A manual run on another branch publishes nothing.

The release tooling is tested apart from the CLI, from the repository root:

```sh
uv run pytest packaging
```

## Configuration

`[tool.semantic_release]` in `pyproject.toml`. Paths in it are relative to the repository root. Preview what the next run would do, from the repository root:

```sh
uv run semantic-release --noop version --print
```

The preview only reports a version on `main`; other branches are not release branches.

## Repository settings

The workflow needs **Settings > Actions > General > Workflow permissions** set to read and write, or the `contents: write` that the `version` and `release` jobs declare is capped. A rule that blocks direct pushes to `main` also blocks the bot; allow `github-actions[bot]` to bypass it.

The `homebrew` job pushes to the tap with the repository secret `HOMEBREW_TAP_GITHUB_TOKEN`: a fine-grained personal access token whose only repository is `bkuberek/homebrew-tap`, with **Contents** read and write. `GITHUB_TOKEN` cannot push to another repository. When the token expires, the `homebrew` job fails at its checkout of the tap; renew the secret and run the workflow by hand ([publishing again](#publishing-again)).
