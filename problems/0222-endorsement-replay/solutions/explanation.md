# Endorsement Replay: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-endorsements | optimal | O(k) per endorse or premium total, O(log k) per premiumOn | O(k) | default answer |

`k` is the number of distinct effective dates, including the term start.

## Approach: sorted-endorsements (Keep endorsements sorted by effective date and sum the segments)

### Intuition

The endorsements define a step function of the full-term premium over the term. Written and earned premium are sums over its steps, so the arrival order of the endorsements must not matter, only their effective dates.

### Algorithm

1. Keep a sorted map from effective date to full-term premium, seeded with `termStart` and the constructor's premium.
2. `endorse`: refuse a date outside `[termStart, termEnd)`. Otherwise insert the date, or replace the premium when the date is already there.
3. `premiumOn`: return `-1` outside the term; otherwise the premium of the greatest effective date that is on or before `onDate` (a floor lookup).
4. Totals: the cutoff is `termEnd` for `writtenPremium`, and `asOfDate` clamped into the term for `earnedPremium`. Walk the segments in date order up to the cutoff; a segment runs from its date to the next date (or the term end) and is cut at the cutoff. Add `premium * days` exactly, divide by `termDays` and round once to cents, half up.

### Correctness

The dates are sorted and distinct and the first one is `termStart`, so every day of the term belongs to exactly one segment, governed by the endorsement with the latest effective date on or before it. Arrival order never matters, except that a later arrival replaces an earlier one on the same date, which is the stated correction rule. The segments before the cutoff cover exactly the term days before it, so the weighted sum divided by `termDays` is the defined amount, and the single rounding is the defined answer.

### Complexity

- Time: O(k) per endorse or premium total, O(log k) per premiumOn — an insert shifts up to k entries and a total walks every segment; premiumOn is one binary search.
- Space: O(k) — one entry per distinct effective date.

### Trade-offs

Replaying the endorsements in arrival order gives wrong answers for back-dated ones. A per-day array costs O(term days) per change and per total. A tree makes inserts O(log k), and prefix sums over the segments make a total O(log k) between changes, at the price of rebuilding them when an endorsement arrives. With at most 1000 calls, the plain sorted list is the right size of answer.

### Pitfalls and edge cases

- Applying endorsements in arrival order instead of effective-date order (`ex2`, `h5`).
- An endorsement on an existing date, including `termStart`, replaces it (`h2`, `h10`, `ex3`).
- The end date is outside the term, for `endorse` and for `premiumOn` (`ex3`, `h7`).
- Rounding every segment instead of the total once (`h6`).
- Earned premium on an endorsement's own date excludes that day (`h10`).
- Earned premium before the start and after the end (`h1`).
- A leap-year term has 366 days (`h4`).
- `premiumOn` returns the stated premium, in canonical form (`h8`).
- Five-year terms and large premiums (`h9`).
- Kotlin's `/` on `BigDecimal`.

### Language notes

- Python: the standard library has no sorted map, so keep two parallel lists and use `bisect_left` to find a slot and `bisect_right` for the floor lookup. `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` rounds once, and `(b - a).days` counts days.
- TypeScript: parallel arrays of `IsoDate` and `Decimal`, a hand-written lower bound on ISO strings (which sort chronologically), and `splice` to insert. Days come from `Date.parse` (date-only ISO strings parse as UTC). `weighted.div(termDays, 2, "HALF_UP")` divides and rounds in one call.
- Java: `TreeMap<LocalDate, BigDecimal>` does the sorting: `put` replaces a same-date entry, `floorEntry(onDate)` answers `premiumOn`, and iterating the entries with a look-ahead to `higherKey` gives the segments. `divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP)` rounds once.
- Kotlin: the same `java.util.TreeMap`. Never divide with `/`: it keeps the dividend's scale and rounds half-even (`h6`: 0.42 / 4 at scale 2 would give 0.10 instead of 0.11). Use `divide(termDays, 2, RoundingMode.HALF_UP)`.
- Go: there is no sorted map in the standard library, so two parallel slices stay sorted by date. `slices.BinarySearchFunc(dates, day, time.Time.Compare)` returns the slot and whether the date is already there (a same-date endorsement overwrites it), and `slices.Insert` shifts the tail. The floor lookup is `sort.Search` for the first date after the day, minus one. Count days as `(end.Unix() - start.Unix()) / 86400`, since `Time.Sub` is a `time.Duration` that stops at about 292 years, and finish with `DivRound(termDays, 2)`, which divides once and rounds half away from zero (`HALF_UP`).
- Rust: two parallel `Vec`s, with `binary_search` on the dates: `Ok(slot)` is a same-date correction and `Err(slot)` is the insertion point, so one `match` covers both. `partition_point(|date| *date <= on_date) - 1` is the floor, which cannot underflow because the first date is `term_start`. `as_of_date.clamp(term_start, term_end)` bounds the cutoff, and `/` on `Decimal` followed by `round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)` rounds once (case `h6`).
