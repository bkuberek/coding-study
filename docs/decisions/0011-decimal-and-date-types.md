# ADR 0011: Decimal and date are scalar types with string wire forms

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-28 |
| Spec | [problem-format](../specs/problem-format.md#decimal-and-date), [runners](../specs/runners.md#execution-environment) |

## Context

The type DSL had `int`, `long`, `double`, `bool`, `string` and `char`, so a problem could not state money or a calendar day the way an interview does: a premium is a `Decimal` (or `BigDecimal`), and a policy period is a pair of dates. With a `double`, a rounding mistake cannot be told apart from a floating-point artifact, and with cents in an `int` the candidate never meets the real API or its rounding modes.

Four constraints shaped the answer:

- Tests are language-neutral JSON, and a comparator runs once, in the CLI, on JSON values, without knowing types ([ADR 0001](0001-data-driven-tests.md)).
- A JSON number becomes a JavaScript number or a Python float, which loses the precision a decimal exists to keep.
- The TypeScript runner, the workspace and the reference build project have no runtime npm dependencies, and a reference under `.cs/build/typescript/ref/` cannot resolve the workspace's `node_modules`. Node 24 has no `Temporal`.
- Every Kotlin type must erase to the Java type, so one JVM runner serves both ([problem-format](../specs/problem-format.md#type-mapping)).

## Decision

- `decimal` and `date` are scalars, so `decimal[]`, `decimal[][]` and `list<decimal>` exist, and likewise for `date`.
- On the wire both are JSON strings. A `decimal` matches `^-?(0|[1-9][0-9]*)(\.[0-9]+)?$` with at most 28 significant digits (Python's default context precision). A `date` is `YYYY-MM-DD`, a real day in years 0001 to 9999.
- Inputs keep their scale: `"2500.00"` reaches the solution with scale 2. Every runner writes a returned decimal in canonical form (no trailing fractional zeros, no `-0`), so `2500.00` and `2500` come back as the same text and the unchanged comparators decide by numeric equality. Check S4 requires expected values to be canonical and names the canonical form when one is not.
- Python uses `Decimal` and `date`, Java and Kotlin use `BigDecimal` and `LocalDate`. The TypeScript `decimal` is a `Decimal` class in `runners/typescript/support.ts`, reached through `#support`: immutable, backed by a `bigint`, with the method names of big.js (`plus`, `minus`, `times`, `div`, `round`, `cmp`, `eq`, `toFixed`), Java's `movePointLeft` and `movePointRight` for exact powers of ten (big.js has none), and the rounding modes of Java's `RoundingMode` except `UNNECESSARY`. The TypeScript `date` is the ISO string.
- Encoders are strict. Python rejects `float`, `int`, non-finite decimals and `datetime` (a subclass of `date`); TypeScript rejects anything that is not a `Decimal` (found by its `unscaled` and `scale` fields, never `instanceof`) and strings that are not real days; the JVM rejects `null` and other classes.
- The Python runner gives every case a fresh `decimal.Context()`, because the context belongs to the thread and a reference that sets the precision or rounding would otherwise leak into later cases.
- Each problem states the scale and rounding mode of its decimal results, because the scale is not compared.

## Consequences

- Comparators, the oracle and generated cases need no change, and the existing problems and their stubs are untouched. Generators return decimals and dates as strings, because `Decimal` and `date` objects are not JSON.
- Authors write expected decimals as `"2500"`, never `"2500.00"`. The `float` comparator applies to JSON numbers only, so it does nothing for a decimal, and check S8 rejects it where the compared outputs hold `decimal` and no `double`.
- The `Decimal` class is about 200 lines to maintain, and its API is not an industry API. It keeps big.js names so the habits transfer, and its unit tests pin the rounding to the results of Python's `decimal` and Java's `BigDecimal`.
- A TypeScript `date` is a `string` in stubs, so the stub does not tell a date from other text. ISO strings sort like dates, and calendar arithmetic uses `Date.UTC`.
- Statements show decimals and dates without quotes, typed by the signature (`2500.50`, `2026-01-01`); failure reports show them as quoted JSON strings.
- The `decimal` and `date` rows keep the JVM erasure property: `Array<BigDecimal>` erases to `BigDecimal[]`.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Decimals as JSON numbers | The value passes through a JavaScript number or a Python float and loses precision before the solution sees it |
| Equality that includes the scale | `2500.00` and `2500` would differ, and the scale depends on each language's division rules (Python follows the context, Java needs an explicit scale), so every TypeScript reference would have to copy them. A missed rounding still fails, because it changes the number |
| Type-aware comparators in the CLI | The types would have to reach every comparator and the checker contract, and the raw-equality assertions of the runner tests would no longer hold |
| decimal.js or big.js in TypeScript | Breaks the no-runtime-dependency setup: both need installing in the runner runtime and the workspace, plus resolving `node_modules` from the reference build project |
| A plain `string` for a TypeScript decimal | Arithmetic on strings is not workable; every reference would embed its own `bigint` helper |
| A `Date` at UTC midnight for a TypeScript date | `new Date(2024, 0, 1)` is not UTC midnight outside UTC, so a correct-looking solution would fail on the owner's machine, and `Date` is mutable |
| A Temporal polyfill | A heavy dependency with the same resolution problem |
| Money as an `int` of cents | The candidate never meets `Decimal`, `BigDecimal` or their rounding modes, which is what the practical problems exercise |
