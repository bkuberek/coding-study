# Endorsement Replay

## Statement

A contractor's policy covers the days `[termStart, termEnd)`: `termStart` is covered and `termEnd` is not. Endorsements change its premium during the term, and they often arrive late: an endorsement dated in the past (back-dated) still takes effect on its own date, not on the day it is entered.

Premiums are stated as full-term premiums: what the whole term would cost at that rate. A stretch of `d` days at full-term premium `p` is worth `p * d / termDays`, where `termDays` is the number of days of the whole term.

Implement the class `EndorsedPolicy`:

- `EndorsedPolicy(termStart, termEnd, fullTermPremium)` creates a policy whose full-term premium is `fullTermPremium` from `termStart`.
- `endorse(effectiveDate, fullTermPremium)`: from `effectiveDate` until the next later effective date (or the end of the term), the full-term premium is `fullTermPremium`. An endorsement with the same effective date as an earlier one, including `termStart`, replaces it. Returns `false`, and changes nothing, when `effectiveDate` is not in `[termStart, termEnd)`; otherwise returns `true`.
- `premiumOn(onDate)`: the full-term premium in force on `onDate`, exactly as stated (not rounded), or `-1` when `onDate` is outside `[termStart, termEnd)`.
- `writtenPremium()`: the premium for the whole term. Each stretch of `d` days at full-term premium `p` contributes `p * d / termDays`; add the exact contributions and round once to cents, half up.
- `earnedPremium(asOfDate)`: the same sum over the days of the term before `asOfDate`, rounded the same way. It is `0` on or before `termStart` and equals the written premium on or after `termEnd`.

Endorsements apply in the order of their effective dates, not in the order they arrive: a back-dated endorsement that arrives after a later-dated one governs only until that later date.

## Input

- `EndorsedPolicy(termStart, termEnd, fullTermPremium)`: the term and the premium in force from its first day.
- `endorse(effectiveDate, fullTermPremium)`: the day the new premium starts and the new full-term premium.
- `premiumOn(onDate)`, `earnedPremium(asOfDate)`: the day to look at.
- `writtenPremium()`: no arguments.

Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for the constructor, a boolean for `endorse`, and a decimal for the other methods. Decimals are compared by value, so `1200.00` and `1200` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

An endorsement on 2026-07-02 doubles the full-term premium. Before it, 1200 applies, and on that date 2400 takes over. The written premium is (1200 * 182 + 2400 * 183) / 365 = 1801.64. Before 2026-10-01 the policy earned 182 days at 1200 and 91 days at 2400: 1196.71.

### Example 2

<!-- case: ex2 -->

The endorsement of 2026-10-01 arrives first, and the back-dated one of 2026-04-01 arrives second. The back-dated one governs only from April until October, so the premium on 2026-05-15 is 5475, and 7300 still applies from October. The written premium is 3650 * 90 / 365 + 5475 * 183 / 365 + 7300 * 92 / 365 = 900 + 2745 + 1840 = 5485.

### Example 3

<!-- case: ex3 -->

The second endorsement on 2026-03-01 corrects the first, so 2000 governs from that date. An endorsement on the end date, and one the day before the start, are refused with `false`. The end date is outside the term, so `premiumOn` returns -1 there. The written premium is (1000 * 59 + 2000 * 306) / 365 = 1838.36.

## Constraints

- At most `10^3` calls in total.
- `termStart < termEnd`, and the term is at most 5 years long.
- `0 <= fullTermPremium <= 10^7`, with at most 2 fractional digits.
- Every date falls between `2000-01-01` and `2100-12-31`.

## Follow-ups

- The return or additional premium of one endorsement: the pro-rated difference, which can be negative.
- Withdraw an endorsement that was entered by mistake.
- List the segments of the term for an audit.
- Many total queries between changes: prefix sums over the segments, or a Fenwick tree when endorsements keep arriving.

## Hints

### Hint 1

Store the initial premium as an endorsement on `termStart`.

### Hint 2

Keep the endorsements sorted by effective date; one with an already-used date replaces the old one.

### Hint 3

Add `premium * days` exactly, then divide by the term's days and round once.
