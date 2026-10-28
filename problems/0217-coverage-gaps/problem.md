# Coverage Gaps

## Statement

A contractor has to be insured continuously across a project window. You get the contractor's policy periods and the window; list every stretch of the window that no policy covers.

Every range, including the window, is half-open `[start, end)`: the start day is covered and the end day is not. So `[2026-01-01, 2026-03-01)` and `[2026-03-01, 2026-04-01)` leave no gap between them, while `[2026-03-01, 2026-03-02)` followed by `[2026-03-03, 2026-04-01)` leaves the one-day gap `[2026-03-02, 2026-03-03)`.

Policies may be unsorted, overlap, nest inside each other, repeat, or lie partly or entirely outside the window. Only the part of a gap inside the window counts.

## Input

- `periods`: the policy periods; `periods[i] = [start, end]` with `start < end`
- `windowStart`, `windowEnd`: the project window `[windowStart, windowEnd)`

Dates are shown as quoted strings in the examples, which is how the tests carry them.

## Output

The uncovered stretches inside the window as `[start, end]` pairs, sorted by start. Each pair is a maximal gap, so no two returned gaps touch or overlap, and each lies within the window. Return an empty list when the window is fully covered, and the whole window when there are no periods.

## Examples

### Example 1

<!-- case: ex1 -->

The first two policies overlap and together cover 2026-01-01 up to 2026-04-01. The third starts on 2026-05-01, so April is uncovered. The window ends on 2026-07-01, the day the last policy ends, so nothing is missing at the end.

### Example 2

<!-- case: ex2 -->

The same policies with a window that ends a month later: July is now uncovered too, so there are two gaps.

### Example 3

<!-- case: ex3 -->

With no policies at all, the whole window is one gap.

## Constraints

- `0 <= periods.length <= 10^4`, and `start < end` for every period.
- `windowStart < windowEnd`.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- Find the gaps across several contractors at once, where each contractor has its own periods.
- Return the total number of uncovered days instead of the gaps.
- Can you process the periods as a stream without sorting all of them first?

## Hints

### Hint 1

Sort the periods by their start date.

### Hint 2

Track the first day that is not yet known to be covered. A period that starts after that day opens a gap.
