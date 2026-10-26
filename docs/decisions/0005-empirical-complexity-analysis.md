# ADR 0005: Empirical complexity analysis against a reference ladder

| Field | Value |
|-------|-------|
| Status | Accepted; the ladder check is calibrated by [ADR 0009](0009-ladder-calibration.md) |
| Date | 2026-10-24 |
| Spec | [performance-analysis](../specs/performance-analysis.md) |

## Context

Passing tests does not show whether a solution is optimal. LeetCode answers this with a crowd percentile, which needs many users and one fixed runtime; this tool has one user, four runtimes and a laptop with noise from GC, JIT compilation, thermal throttling and background load. Static analysis of user code cannot determine complexity in general.

## Decision

- Each problem ships several reference approaches (brute, intermediate, optimal) tagged with declared time and space classes, plus a seeded input generator.
- `cstudy bench` runs the user's code and all references in one runtime process on identical inputs across a size ladder, with warmup, repetitions and round-robin ordering.
- Growth is classified by a log-log slope fit into coarse bands. Within a band, the verdict uses the ratio to the fastest optimal reference at the largest common size and the trend of that ratio.
- Every verdict carries a confidence level derived from fit quality, spread and environment; memory confidence is capped per runtime.
- Ranking is against the ladder and the user's own history, stored in `progress.db`.
- Optional time limits derive from the calibrated optimal reference in the same language; they are off by default.

## Consequences

- Content cost rises: every `ready` DSA problem needs at least one optimal approach in each language, a Python oracle approach and a generator.
- The tool distinguishes polynomial degrees and constant versus linear space reliably, but cannot separate n from n log n by slope, nor the sublinear classes from each other; it says so instead of guessing.
- Memory numbers are not comparable across languages; the UI only compares within a language.
- Bench runs take seconds to a minute, so they are opt-in (`cstudy bench`, `cstudy test --perf`), never part of plain `cstudy test`.
- References are themselves validated (`cstudy verify --ladder`), which catches weak generators that never stress the algorithm.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Crowd percentile ("beats X%") | No crowd; any number would be invented |
| Static complexity analysis of user code | Undecidable in general; brittle across 4 languages |
| Single large-input timing | Cannot separate constant factors from growth; no confidence measure |
| Fixed absolute time limits per problem | Depend on machine and language; the reference-relative factor adapts to both |
| Fine-grained classification (n versus n log n by slope) | Noise exceeds the signal at practical sizes; would produce false precision |
