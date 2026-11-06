# Debug: Local Day Boundaries

## Statement

A daily report counts a shop's orders by the shop's own calendar day. `placedAt[i]` is the moment order `orderIds[i]` was placed, as an ISO 8601 timestamp with a zone. `day` is the calendar day the report is for, as `YYYY-MM-DD`, and `utcOffsetMinutes` is the shop's offset from UTC: `-300` for five hours behind, `540` for nine hours ahead.

`ordersOnLocalDay` returns the ids of the orders placed during that day in the shop's zone, from its local midnight, included, to its next local midnight, not included, in input order. The offset is fixed for the whole day.

A developer already fixed one report of this bug last month. Find what is still wrong, and fix it.

### Bug report

> **Title:** Monday's report has Sunday night's orders in it
>
> Our New York shop, at `-300`, sees orders from the evening before in each day's count. Our Tokyo shop, at `540`, has the opposite problem: orders placed before nine in the morning are missing from the day and appear nowhere. Last month's fix took care of the late-night orders that used to fall off the end of the day. Everything looks right around noon.

## Input

- `orderIds`: the orders' ids
- `placedAt`: `placedAt[i]` is when `orderIds[i]` was placed, ending in `Z` or in an offset such as `-05:00`
- `day`: the calendar day, in the shop's zone
- `utcOffsetMinutes`: the shop's offset from UTC, fixed for that day

## Output

The ids of the orders placed on that local day, in input order.

## Examples

### Example 1

<!-- case: ex1 -->

In New York, 17:00 UTC is noon, so the first order is on the 5th and the second is on the 6th. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

At offset 0, the local day is the UTC day. This case passes as shipped too.

## Constraints

- `0 <= orderIds.length == placedAt.length <= 1000`
- Every timestamp and day is valid, and within the years 2000 to 2100.
- `-720 <= utcOffsetMinutes <= 840`
- Your answer must not depend on the time zone of the machine it runs on.

## Follow-ups

- A real shop's offset changes twice a year in many places, so one local day can be 23 or 25 hours long. What input would this function need instead of an offset, and what would you use to compute with it?
- Should your database store the moment an order was placed, the local day it belongs to, or both? What goes wrong with each?

## Hints

### Hint 1

In a Node prompt, try `new Date("2026-11-05").toISOString()`. Which moment is that, in which zone?

### Hint 2

Local midnight in a zone five hours behind UTC happens at 05:00 UTC. Work out, as a formula with `utcOffsetMinutes`, when local midnight happens.

### Hint 3

`dayEnd` is already right in the code as shipped. How long is the window it describes?

### Hint 4

Run your fix with `TZ=Asia/Tokyo` and `TZ=UTC` in the environment. A correct answer gives the same result under both.
