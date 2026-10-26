# ADR 0008: An installable tool with separate workspaces

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-25 |
| Spec | [installation-and-workspaces](../specs/installation-and-workspaces.md) |
| Amends | [ADR 0002](0002-python-uv-cli.md) (install), [ADR 0003](0003-gradle-wrapper-jvm.md) (where the wrapper lives) |

## Context

Until now the repository was also the workspace: `workspace/` held the practice projects, `progress.db` and `.cs/` sat at the repository root, and `cstudy` found everything by walking up to the directory with `problems/` and `schemas/`. The owner wants to install `cstudy` on any device and practice in a separate workspace that is versioned on its own, so solutions are never committed and pushed to this repository, which is about to become public. The workspace may be the current directory or be named on the command line.

Two constraints shape the design. The runners must be built where tools can write: Gradle builds an included build in place (`build/`, `.gradle/`), and uv and pnpm write next to the project they install, so pointing a workspace at runners inside the installed package would write into `site-packages`. And a workspace is meant to move between machines in git, so its tracked files cannot hold machine-specific absolute paths.

## Decision

- The repository root is the installable project (hatchling, `pyproject.toml` at the root): `uv tool install git+https://github.com/bkuberek/coding-study` and `pipx install git+...` work without `#subdirectory`. The wheel bundles `problems/`, `tracks/`, `runners/` and `schemas/` as `coding_study/content/`, and the workspace templates as package data. Every bundled path is inside the project root, so a wheel built from the sdist equals one built from the checkout.
- Content and workspace are two roots. Content: `--content`, `CSTUDY_CONTENT`, the bundled copy, then the checkout `cstudy` runs from. Workspace: `--workspace`, `CSTUDY_WORKSPACE`, the nearest ancestor with `.cs/workspace.toml`, then the current directory. Commands that need a workspace exit 3 without one and point at `cstudy init`.
- `cstudy init` scaffolds a workspace from the templates (the former `workspace/` directory, removed from the repository); it never overwrites a file and never commits.
- Each workspace materializes the runners into `.cs/runtime/runners/` and refreshes that copy when the content's digest changes. The practice projects reach it through relative paths (`../.cs/runtime/runners/...`), so nothing absolute is tracked and nothing is ever written into the installed package.
- The workspace's own `problems/` is overlaid on the catalog by slug; the workspace problem wins a collision.

## Consequences

- The repository holds only code and content. Its `.gitignore` and the `cstudy init` refusal inside a checkout guard against a workspace created there by mistake.
- Developers and the tests use an external workspace (`CSTUDY_WORKSPACE`, temporary fixtures); `cstudy verify` in a checkout reads the checkout's content and builds with that workspace's toolchains.
- Each workspace pays one Gradle build of the runner, the support classes and the plugin (seconds, once per runner change), and holds a copy of the runner sources (under 1 MB).
- An upgrade of `cstudy` refreshes `.cs/runtime/` on the next run; `cstudy doctor` reports a stale runtime, missing template files, or a workspace schema newer than the running `cstudy`.
- `CS_ROOT` is removed. The paths `cstudy` prints are relative to the workspace (`python/practice/two_sum.py`, `.statements/two-sum.md`).
- The project's version and dependencies move from `cli/pyproject.toml` to the root `pyproject.toml`; the CLI's tool settings move to `cli/ruff.toml`, `cli/pyrightconfig.json`, `cli/pytest.ini` and `cli/.importlinter`, because a `pyproject.toml` in `cli/` would make uv treat `cli/` as a separate project.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Install from `#subdirectory=cli` with a build hook or `force-include` reaching `../problems` | Works only when the wheel is built straight from a checkout; a wheel built from the sdist (`uv build`, pip) has no `..` and ships without content |
| Point the workspace at the bundled runners by absolute path, written into workspace config | Gradle and uv write build output into `site-packages`, an upgrade or a second machine invalidates the tracked path, and IntelliJ imports break when the path moves |
| One shared runtime in a user cache directory | Saves a copy per workspace but needs version keying across workspaces that may run different `cstudy` versions, and the relative wiring would become absolute again |
| Keep the repository as the default workspace, with `.gitignore` rules for solutions | The owner's requirement: solutions must not live in the public repository at all, and a separately versioned workspace is the point |
| Bundled content wins a slug collision | After an upgrade adds that slug, `cstudy test` would judge your own solution against a different problem's tests, and your problem would vanish from the catalog |
