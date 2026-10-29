# ADR 0013: Homebrew distribution from GitHub releases

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-29 |
| Spec | [versioning](../specs/versioning.md#homebrew-tap), [installation-and-workspaces](../specs/installation-and-workspaces.md#install) |
| Amends | [ADR 0008](0008-installable-tool-and-separate-workspaces.md) (install) |

## Context

`cstudy` installed only with `uv tool install git+https://github.com/bkuberek/coding-study` or pipx, which builds whatever the default branch holds and needs uv or pipx first. The owner wants `brew install bkuberek/tap/cstudy` to install the released version, and every release to reach the tap without a manual step. A release was a git tag and nothing else: no GitHub release, no files.

Four constraints shaped the answer:

- The tag and the release commit are pushed with `GITHUB_TOKEN`, whose events start no workflow, so a workflow triggered by the tag or by a GitHub release would never run.
- Three runtime dependencies are compiled extensions: pyyaml, and rpds-py and watchfiles, which are written in Rust. Homebrew's `std_pip_args` pass `--no-binary=:all:`, so the standard Python formula pattern builds each of them from source.
- On macOS, Homebrew rewrites the install name of every dylib in a keg to an absolute path. The prebuilt watchfiles extension has an `@rpath` install name and no header room for a longer one, so the rewrite fails the install.
- `uv.lock` already pins every dependency with the hashes of its published files, and `uv export` writes them as a requirements file.

## Decision

- Each release attaches two files to a GitHub release `vX.Y.Z`: the pure-Python wheel (`uv build --wheel`) and `requirements.txt` (`uv export --locked --no-dev --no-emit-project`, with hashes). The release notes are the tag's `CHANGELOG.md` section.
- The tap `bkuberek/homebrew-tap` holds `Formula/cstudy.rb`, rendered from `packaging/homebrew/cstudy.rb.template` in this repository with the URLs and sha256 of the two files. Nothing is uploaded to PyPI.
- The formula creates a virtual environment on `python@3.13` in `libexec`, installs the requirements with `pip --require-hashes --only-binary=:all: --no-deps` (binary wheels from PyPI), installs the wheel, links `cstudy`, and declares `preserve_rpath` so Homebrew keeps the `@rpath` install names. Python loads an extension by its file path, so the kept name is never resolved.
- Publishing is two jobs of `.github/workflows/version.yml` after the `version` job: `release` (with `GITHUB_TOKEN`) and `homebrew` (with `HOMEBREW_TAP_GITHUB_TOKEN`, a token scoped to the tap). They run for a tag the run created, and a manual run publishes the newest tag again. Each skips what is already done.
- The language toolchains (uv, Node.js and pnpm, a JDK) are not formula dependencies. `cstudy doctor` checks them and links to [install the language toolchains](../guides/toolchains.md).

## Consequences

- A Homebrew install is the released version, with exactly the dependency versions of `uv.lock`, each checked against its hash.
- There are no bottles: every install builds the virtual environment, which takes seconds, and needs network access to PyPI. Homebrew allows network access while building a formula that defines no `fetch` phase, unless `HOMEBREW_FORMULA_BUILD_NETWORK=deny` is set.
- The formula works wherever PyPI has binary wheels of every dependency for Python 3.13. It is installed and tested on macOS arm64; Linux is untested.
- The formula pulls in `python@3.13` (which `uv python find 3.13` then also finds for the workspace).
- A `cstudy` installed with uv or pipx earlier on `PATH` shadows the Homebrew one; Homebrew warns about it at install, and the formula's caveats say so.
- The formula uses `Formula#python3` and `preserve_rpath`, as `brew audit --strict` asks; both exist in Homebrew 7.
- A template change reaches the tap only with the next publish, or with a manual run of the workflow.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Upload to PyPI and generate one `resource` per dependency (`brew update-python-resources`) | Adds a PyPI project and its credentials, and the resources are sdists that Homebrew builds from source; rpds-py and watchfiles need a Rust toolchain at every install |
| Build from source in the formula (`depends_on "rust" => :build`) | Installs a Rust toolchain and compiles two extensions on every install |
| One `resource` per binary wheel, chosen with `on_macos`, `on_linux`, `on_arm` and `on_intel` | A wheel per platform for each compiled dependency, regenerated each release; `Virtualenv#pip_install` hands pip only a pure-Python wheel resource as a file, so each platform wheel needs its own install code |
| A workflow triggered by the tag or the GitHub release | Never runs, because both are created with `GITHUB_TOKEN` |
| A personal access token for the version job, so the tag triggers a release workflow | Gives the version job a long-lived token and reopens the loop that `GITHUB_TOKEN` prevents |
| `brew bump-formula-pr` or a third-party bump action | Updates `url` and `sha256` of an existing formula but not the requirements resource, and a third-party action would hold the tap token |
| A `fetch` phase that downloads the wheels, then an offline install | Stricter sandboxing, but a second code path in the formula for a personal tap; revisit if Homebrew denies network access during builds by default |
