# Versioned Rate Table

## Statement

A rating service has to reproduce any past price exactly, so its rate tables are never edited in place. A change is published as a new version with an effective date, and every older version stays available.

Implement the class `RateTable`:

- `RateTable()` creates an empty table with no versions.
- `publish(effectiveDate, classCodes, rates)` adds a version in which the class `classCodes[i]` costs `rates[i]`. The first call creates version 1, the next version 2, and so on, in the order of the calls.
- `rateAsOf(onDate, classCode)` returns the rate of `classCode` in the version that governs `onDate`. It returns `-1` when no version governs that day, or when the governing version does not list the class.
- `versionAsOf(onDate)` returns the id of the version that governs `onDate`, or `-1` when there is none.

The version that governs a day is the one with the latest effective date that is on or before that day: a version is in force **on** its effective date. When several versions share an effective date, the one published last wins, because it is a correction of the earlier ones. A version is a complete table: it never inherits classes from older versions, so a class that a newer version leaves out is not found, even if an older version listed it. Versions may be published in any date order.

## Input

- Constructor: no arguments.
- `publish(effectiveDate, classCodes, rates)`: the first day the version applies, the class codes and, in the same order, their rates.
- `rateAsOf(onDate, classCode)`: the day of the quote and the class being priced.
- `versionAsOf(onDate)`: the day of the quote.

Each test is a sequence of calls: the constructor first, then the other calls in order. Dates and decimals are shown as quoted strings in the examples, which is how the tests carry them.

## Output

The expected output lists one result per call: `null` for the constructor and for every `publish`, a decimal for `rateAsOf`, and an integer for `versionAsOf`. Decimals are compared by value, so `13.10` and `13.1` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

Version 1 starts on 2026-01-01 at 12.50 and version 2 starts on 2026-07-01 at 13.10. A quote in March is priced by version 1. A quote on 2026-07-01 itself is priced by version 2, because a version is in force on its effective date.

### Example 2

<!-- case: ex2 -->

Before the only version starts (2026-03-31) there is no rate and no version, so both return `-1`. Class `8810` is not in the version, which also gives `-1`. A rate of `18.00` comes back as `18`.

### Example 3

<!-- case: ex3 -->

The 2026-07-01 table is published first and the 2026-01-01 table second; the order of publishing does not change which one governs a day. Version 3 is published for the same effective date as version 1 and corrects its rate to 13.25, so from 2026-07-01 version 3 governs.

## Constraints

- At most `10^4` calls in total.
- `0 <= classCodes.length == rates.length <= 100`; the codes of one version are distinct and 1 to 8 characters long.
- `0 < rates[i] < 10^4`, with at most 4 fractional digits.
- Dates fall between `2000-01-01` and `9999-12-31`.

## Follow-ups

- If publishing becomes frequent, how would a balanced tree (Java `TreeMap`) change the cost of `publish`?
- Store the version id on every quote, so a price can be reproduced without knowing the date.
- Retire a version without deleting it, so it stops governing but can still be audited.

## Hints

### Hint 1

Keep the versions sorted by effective date.

### Hint 2

"The latest effective date on or before the day" is an upper-bound binary search, minus one.

### Hint 3

Insert a version with an already-used date after the existing ones with that date, so the last one published stays last.
