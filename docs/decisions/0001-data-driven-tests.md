# ADR 0001: Tests are data, not per-language code

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Spec | [problem-format](../specs/problem-format.md), [runners](../specs/runners.md) |

## Context

Every problem must be solvable and checked in Python, TypeScript, Java and Kotlin. Hand-written test files per language multiply authoring cost by four and drift apart as cases are added to one language and not the others.

## Decision

- Each problem has one language-neutral `tests.json`; signatures are declared once in a type DSL in `meta.yaml`.
- One runner per runtime (Python, TypeScript, JVM for Java and Kotlin) loads cases, invokes the target and serializes the output.
- The CLI core judges outputs with comparators written once in Python: `exact`, `unordered`, `unordered-nested`, `float`, `checker`, `ops`.
- Correctness is behavioral: user code is executed and its output compared; reference code is never compared with user code.

## Consequences

- Adding a case or a language-agnostic check is one edit.
- The type DSL and its per-language mapping become the hardest component; a conformance suite guards it.
- Problems needing structures outside the DSL (shared nodes across inputs, maps) need a DSL extension or a checker.
- Runners stay small, so supporting a new language later means one runner and one stub generator.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| pytest, vitest, JUnit and Kotlin tests per problem | 4x authoring cost; drift between languages |
| Generate per-language test files from data | Same data model plus four test frameworks to keep in sync; slower runs |
| Comparators inside each runner | Three implementations of float, multiset and checker logic |
