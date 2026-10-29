# Certificate Expiry Alerts

## Statement

A general contractor keeps certificates of insurance from its subcontractors and must chase any subcontractor whose coverage has lapsed or is about to. Each certificate has an expiry date: the first day it no longer proves coverage.

A subcontractor may have several certificates on file. A renewal supersedes the older ones, so only the latest expiry date of each subcontractor matters.

On `asOfDate`, report every subcontractor whose latest expiry date is on or before `asOfDate` (status `expired`), or falls within the next `windowDays` days, up to and including `asOfDate + windowDays` (status `expiring`). A subcontractor whose coverage ends later than that is not reported. Return rows `[contractorId, expiryDate, status]`, ordered by expiry date and then by contractor id.

## Input

- `contractorIds`, `expiryDates`: one certificate per position, in any order; `contractorIds[i]` holds the certificate that expires on `expiryDates[i]`
- `asOfDate`: the day to check
- `windowDays`: how many days ahead count as "about to expire"

## Output

The rows `[contractorId, expiryDate, status]`, with the date as `YYYY-MM-DD` text and the status `expired` or `expiring`. Ids compare character by character, so `"sub-10"` comes before `"sub-9"`.

## Examples

### Example 1

<!-- case: ex1 -->

The window ends on 2026-12-01. Two certificates expire within it: 2026-11-05 and 2026-11-15, in that order. The electrician's certificate runs to March 2027, so it is not reported.

### Example 2

<!-- case: ex2 -->

The plumber's first certificate expired on 2026-10-15, but a renewal runs to 2027-10-15, so only the latest date counts and the plumber is not reported. The paving contractor's only certificate expired on 2026-10-20, so it is reported as expired.

### Example 3

<!-- case: ex3 -->

An expiry on `asOfDate` itself is already expired. The window runs up to and including 2026-12-01 (`asOfDate` plus 30 days), so the second certificate is expiring. One day later falls outside the window.

## Constraints

- `0 <= contractorIds.length == expiryDates.length <= 10^4`.
- Ids are 1 to 20 characters of `[a-z0-9-]`.
- `0 <= windowDays <= 3650`.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- A different window per subcontractor, for example by trade.
- Several coverage lines per certificate (general liability, auto, workers' compensation), each with its own expiry.
- Only the `k` most urgent rows, using a heap.

## Hints

### Hint 1

One pass keeps each subcontractor's latest expiry date.

### Hint 2

Sort `(date, id)` pairs; ISO date text already sorts in date order.
