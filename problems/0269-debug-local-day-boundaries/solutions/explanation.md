# Debug: Local Day Boundaries: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| local-midnight-in-utc | optimal | O(n) | O(n) | default answer: turn the local day into two instants, and compare instants |

## Approach: local-midnight-in-utc (Local midnight as an instant)

### Intuition

`new Date("2026-11-05")` looks like "the 5th", and it is really one moment: midnight UTC. That is what the ECMAScript specification says a date-only string means. For a shop in New York, midnight UTC is 19:00 on the 4th, so the window opens five hours early, and last night's orders fall in it.

The earlier fix moved `dayEnd` by the offset, which was correct and made the bug harder to see: the window now has the right end and the wrong start. At `-300` it is 29 hours long, and at `+540` only 15 hours long. The orders around noon are always inside, so nobody saw a problem in the middle of the day.

The fix is to move both ends: local midnight as an instant is `Date.parse(day) - offset`. The sign is the part to work out rather than guess: nine hours ahead of UTC, midnight has already happened nine hours before midnight UTC.

### Say it out loud

"`new Date` of a date-only string is midnight UTC, not local midnight. A date with a time and no offset, though, is local to the machine, so those two look alike and differ. A day isn't one thing: it's a window of instants, and which window depends on the zone. So I turn the local day into start and end instants and compare instants, and nothing depends on where the code runs."

### Debugging approach

1. **Print the window.** Log `new Date(dayStart).toISOString()` and the same for `dayEnd`. Seeing `2026-11-05T00:00:00.000Z` as the start of a New York day is the whole bug.
2. **Check its length.** A day's window should be 24 hours. At `-300` this one is 29.
3. **Test the edges, in two zones on both sides of UTC.** Around noon, nothing fails. One second either side of local midnight is where this lives.
4. **Check the half-fixes.** `new Date(day + "T00:00:00")` is midnight in the *machine's* zone, which can match at most one shop (`h1` and `h2`). Flipping the sign fails both too. `placedAt[i].startsWith(day)` compares text, whatever zone it is in (`h1`, `h6`). Comparing a shifted date with `getDate()` reads the machine's zone: on a server in UTC it passes, on a laptop it doesn't.

### Algorithm

1. `dayStart` is `Date.parse(day)`, which is midnight UTC, minus the offset in milliseconds.
2. `dayEnd` is `dayStart` plus 24 hours.
3. Keep each order whose instant is in `[dayStart, dayEnd)`.

### Correctness

An instant `t` shows the local wall clock `t + offset`. It falls on `day` when `t + offset` is in `[D, D + 24h)`, where `D` is that day's midnight UTC. Subtracting the offset gives `t` in `[D - offset, D - offset + 24h)`, the window computed here. `Date.parse` reads an offset or a `Z` on a timestamp, and treats a date-only string as UTC, so nothing reads the machine's zone. The half-open window assigns each instant to exactly one day.

### Complexity

- Time: O(n) — one comparison per order; parsing a short timestamp is O(1).
- Space: O(n) — the returned ids.

### Trade-offs

Shifting each order's instant by the offset and comparing its UTC date string to `day` is correct too, and it's a good choice if you are grouping orders by day, because each order computes its own day. Working out one window is simpler for a single day, and it translates directly to `WHERE placed_at >= :start AND placed_at < :end`, which can use an index on `placed_at`.

### Pitfalls and edge cases

- The general trap: `new Date("2026-11-05")` is UTC, `new Date("2026-11-05T00:00:00")` is local to the machine, and `getDate()`, `getHours()` and `setHours()` read or write the machine's zone. Only the `UTC` methods and `toISOString` don't.
- Code like this passes on a server set to UTC, or on the laptop of whoever wrote it, and fails elsewhere. If your bug depends on `TZ`, run your tests with `TZ=Asia/Tokyo` and with `TZ=America/Los_Angeles`.
- A window's end is exclusive. An order at exactly the next local midnight belongs to the next day (`h3`).
- Offsets aren't whole hours (`h5`), and they run from -12 to +14.
- A timestamp's text isn't its day. `2026-11-05T01:00:00+09:00` starts with the 5th, and at `-300` it is the 4th (`h6`).
- A fixed offset isn't a time zone. Where clocks change, a local day can be 23 or 25 hours long, and the offset depends on the date. This problem states a fixed offset so that you can see the window clearly. Real code takes a zone name such as `America/New_York`, and works out the offset for that date.

### Prevention

- Store instants in UTC, and treat a local day as a window you compute at the edge.
- Keep a calendar day as a plain string or a date-only type, and never let it pass through `new Date` by accident.
- Run the test suite under a non-UTC `TZ` in CI, so a hidden dependency on the machine's zone fails there first.

### Language notes

TypeScript types `Date` as one thing, so an instant and a calendar day look the same to the compiler. The newer `Temporal` API makes the difference a type (`Instant`, `PlainDate`, `ZonedDateTime`), where a runtime provides it. Until then, `Intl.DateTimeFormat` with a `timeZone` option is the built-in way to read a wall clock in a named zone.
