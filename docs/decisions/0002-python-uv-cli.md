# ADR 0002: Python and uv for the CLI

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Spec | [architecture](../architecture.md), [cli](../specs/cli.md) |
| Amended by | [ADR 0008](0008-installable-tool-and-separate-workspaces.md): installed from the repository root with bundled content |

## Context

The CLI orchestrates subprocesses, reads YAML, JSON and Markdown, validates JSON Schema, stores SQLite data, watches files and generates code. Content code (generators, checkers, oracles) must run somewhere, and the owner is fluent in Python.

## Decision

- The CLI is a Python 3.13 package in `cli/`, managed with uv and installed as a tool with `uv tool install --editable ./cli`, which puts `cstudy` on `PATH`.
- Generators and checkers are stdlib-only Python and run in the CLI process; oracle approaches run through the Python runner.
- Libraries: Typer, Rich, PyYAML, jsonschema, watchfiles; pytest, ruff, pyright and import-linter for development.

## Consequences

- One language for orchestration, comparators, codegen and content tooling.
- Python start-up (roughly 100 to 300 ms with imports) is acceptable against NFR-2; lazy imports keep `cstudy list` fast.
- The editable install means CLI changes take effect without reinstalling.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Go single binary | Fast start-up, but content tooling would still need Python, giving two toolchains |
| TypeScript on Node | Viable, but weaker for SQLite and scientific fitting; the owner prefers Python for tooling |
| Kotlin or Java | JVM start-up on every command |
