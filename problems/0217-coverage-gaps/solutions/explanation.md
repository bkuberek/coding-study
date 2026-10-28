# Coverage Gaps: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-and-sweep | optimal | O(n log n) | O(n) | default answer |

## Approach: sort-and-sweep (Sort periods by start and sweep a coverage cursor)

### Intuition

This is merge-intervals that reports the holes between the merged runs instead of the runs themselves. Walking the periods by start date, a single cursor remembers how far coverage is known to reach.

### Algorithm

1. Sort a copy of the periods by start date.
2. Set the cursor to `windowStart`.
3. For each period in order: stop if the cursor has reached `windowEnd`. If the period starts after the cursor, report the gap `[cursor, min(start, windowEnd))`. Then move the cursor to the later of itself and the period's end.
4. After the loop, if the cursor is still before `windowEnd`, report the final gap `[cursor, windowEnd)`.

### Correctness

Invariant: every day of `[windowStart, cursor)` is either covered or already reported. A period that starts after the cursor proves that the days between them are covered by nothing, because periods are processed by start date and no later period starts earlier. A period that starts at or before the cursor extends coverage to its end, and the maximum keeps the cursor from moving backwards when a period is nested inside an earlier one. Clipping each gap to the window and stopping at its end keeps all output inside the window.

### Complexity

- Time: O(n log n) — the sort dominates; the sweep itself is one pass.
- Space: O(n) — the sorted copy and the output.

### Trade-offs

Marking every day of the window is simple but costs time proportional to the calendar length rather than the number of policies. The sweep needs the sort; if the periods already arrive sorted, the same loop runs in O(n). Merging the periods first and then reading the holes between the merged runs is equivalent and uses an extra pass.

### Pitfalls and edge cases

- Treating an end date as covered turns touching periods into a gap or a false overlap (`h2`).
- Not clipping to the window: periods before or after it must not create or hide gaps (`h4`, `h7`, `h10`).
- A nested period must not move the cursor backwards, which is why it takes the maximum (`h5`).
- Identical periods (`h8`) and a one-day gap (`h6`) are ordinary input; so is the leap day (`h11`).
- Never report a gap that starts at or after the window's end.
- Sorting the caller's array in place changes the input; sort a copy.

### Language notes

- Python: dates compare directly, and `sorted` on `(start, end)` tuples sorts by start. Dates are plain `date` values.
- TypeScript: a date is an `IsoDate`, a plain ISO string, so `<` and `>` compare chronologically; sort a copy with a comparator on the first element.
- Java: the result is `LocalDate[][]`; copy the input with `clone()`, sort with `Comparator.comparing(period -> period[0])`, and convert the gap list with `toArray(new LocalDate[0][])`.
- Kotlin: `sortedBy { it[0] }` returns a sorted copy, `maxOf` works on `LocalDate`, and `toTypedArray()` converts the gap list to `Array<Array<LocalDate>>`.
