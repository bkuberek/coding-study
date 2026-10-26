# ADR 0004: Original problem wording

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Spec | [content](../specs/content.md#copyright-policy) |

## Context

LeetCode problem statements, examples, test data, editorials and community solutions are copyrighted. The catalog reuses well-known problems because interviewers ask them, and the repository may become public later.

## Decision

- Every statement, example, test case, reference solution and explanation is original work.
- Problem names, function signatures and the underlying algorithmic ideas may match the originals; `meta.yaml` links the original as a reference.
- Personal study guides are referenced by path, not copied.

## Consequences

- Authoring takes longer: each statement is written from scratch.
- The repository can be published without takedown risk from copied text.
- Original wording forces understanding of each problem, which is itself study.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Copy statements verbatim | Infringes copyright; blocks publication |
| Link only, no statement | The CLI loop would require a browser, contradicting the IDE-first goal |
| Close paraphrase | Still a derivative of the protected text |
