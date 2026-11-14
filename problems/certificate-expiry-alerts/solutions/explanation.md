# Certificate Expiry Alerts: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| latest-per-contractor | optimal | O(n + m log m) | O(m) | default answer |

`n` is the number of certificates and `m` the number of distinct subcontractors.

## Approach: latest-per-contractor (Keep each contractor's latest expiry then filter and sort)

### Intuition

Collapse the certificates to one date per subcontractor, and the rest is a filter and a sort.

### Algorithm

1. One pass over the certificates keeps, for each id, the latest expiry date.
2. The horizon is `asOfDate + windowDays`.
3. Keep the ids whose date is on or before the horizon, and label each one `expired` when its date is on or before `asOfDate`, `expiring` otherwise.
4. Sort the rows by date, then by id.

### Correctness

A renewal can only extend coverage, so the latest date decides the status of a subcontractor. The two inequalities, `expiry <= asOfDate` and `asOfDate < expiry <= horizon`, split the reported dates into the two statuses without overlap, and everything beyond the horizon is dropped. The sort key is the whole row key, so the order is the one the statement defines.

### Complexity

- Time: O(n + m log m) — one pass over the certificates, then a sort of at most m rows.
- Space: O(m) — the latest expiry per subcontractor.

### Trade-offs

Sorting every certificate first costs O(n log n) and still needs the per-id collapse. When only the `k` most urgent rows are needed, a heap gives them in O(m log k).

### Pitfalls and edge cases

- Both boundaries are inclusive in the flag: `asOfDate` is expired and `asOfDate + windowDays` is expiring (`ex3`, `h2`, `h10`).
- Judging each certificate on its own instead of the latest one per subcontractor (`ex2`, `h7`).
- The same certificate filed twice gives one row (`h4`).
- Ids order as text, so `sub-10` comes before `sub-9` (`h3`).
- Date arithmetic across the leap day and over long windows (`h5`, `h8`).
- No certificates on file (`h1`) and input order (`h10`).

### Language notes

- Python: `datetime.date` compares and adds `timedelta(days=window_days)`. Sorting `(expiry, contractor)` tuples sorts by date and then by id in code point order.
- TypeScript: a date is an `IsoDate`, a plain ISO string, so `<` compares chronologically. The horizon comes from `new Date(Date.parse(asOfDate) + windowDays * 86_400_000).toISOString().slice(0, 10)`. Sort with a comparator written with `<`, not `localeCompare`, which orders `sub-10` and `sub-9` by locale rules.
- Java: `HashMap.merge(id, expiry, (a, b) -> a.isAfter(b) ? a : b)` keeps the latest date; `asOfDate.plusDays(windowDays)` is the horizon. Sort the entries with `Map.Entry.<String, LocalDate>comparingByValue().thenComparing(Map.Entry.comparingByKey())`; `String.compareTo` is code unit order. The result is `String[][]`.
- Kotlin: `maxOf` merges dates, `plusDays(windowDays.toLong())` is the horizon, `sortedWith(compareBy({ it.value }, { it.key }))` sorts, and `map { arrayOf(...) }.toTypedArray()` builds the `Array<Array<String>>`.
- Go: a map iterates in random order, so the sort is what makes the answer deterministic. `slices.SortFunc` takes a three-way comparison: `a.expiry.Compare(b.expiry)` for the date, then `strings.Compare` on the ids, which orders bytes like Python and Java (so `sub-10` comes before `sub-9`). `asOfDate.AddDate(0, 0, windowDays)` adds whole days, which does not clamp or drift in UTC, and `Format(time.DateOnly)` prints `YYYY-MM-DD`.
- Rust: `entry(id).and_modify(...).or_insert(expiry)` keeps the latest date per contractor. The flagged pairs are `(NaiveDate, String)` tuples, and tuples sort by date first and then by `String`'s byte order, so `flagged.sort()` needs no comparator. `as_of_date + TimeDelta::days(n)` is the horizon, and `NaiveDate::to_string()` is already `YYYY-MM-DD`.
