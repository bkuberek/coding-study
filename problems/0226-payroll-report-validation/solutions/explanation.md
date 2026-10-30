# Payroll Report Validation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| single-pass-checks | optimal | O(L) | O(n) | default answer |

`L` is the total length of the input and `n` the number of rows.

## Approach: single-pass-checks (Check every field of every row in one pass and remember keys for duplicates)

### Intuition

Validation is a list of independent checks. Collecting every error means there is no early exit, and the only rule that crosses rows needs a set of keys.

### Algorithm

1. For each row, in order: if it does not have exactly four values, add `column-count` and move on.
2. Run one check per field in column order; each returns a reason or nothing. Add an error for every reason.
3. If the contractor id, the class code and the period start all passed, form their key. If the key is already in the set, add the `duplicate` error. Then add the key to the set.

### Correctness

Each rule is checked exactly once per row, in the stated order, so the errors come out in the required order: rows ascending, columns in order, and the duplicate error last. A key enters the set only when its three fields passed, so invalid keys never collide, and the payroll plays no part in the key. Rows with the wrong number of values are skipped before any field is read.

### Complexity

- Time: O(L) — every character is examined a constant number of times; set operations are O(1) on average per key.
- Space: O(n) — at most one stored key per row, each bounded by the value length limit.

### Trade-offs

A schema or validation library helps in production but hides the rules in an interview. Stopping at the first error is simpler and worse for the user, who has to upload again and again.

### Pitfalls and edge cases

- Stopping at the first error.
- Unicode digits: a class code of Arabic-Indic digits is invalid (`h7`).
- Lenient date parsing and days that roll over into the next month (`h3`).
- Payroll shapes (`007.5` is valid, `5.`, `.5`, `1e5`, `-5` and `1,000` are not) and the zero and maximum bounds (`h4`, `h2`).
- Sorting error text instead of keeping the natural order: as text, row 10 comes before row 2 (`h5`).
- Duplicates of invalid keys never count, and a duplicate is reported even when the payroll is invalid (`h6`).
- Rows with the wrong number of values are skipped entirely (`ex3`, `h9`).
- Id length and characters (`h8`) and trimming: values are never trimmed.

### Language notes

- Python: write `[0-9]`, never `\d`, which matches the digits of other scripts (`h7`), and use `fullmatch`. `date.fromisoformat` accepts `20260101` and other shapes since Python 3.11, so run the shape check first (`h3`); it raises `ValueError` for 30 February and for year 0.
- TypeScript: anchored regexes with `[0-9]`. `Date.parse("2026-02-30")` is a number in V8 (it rolls over to 2 March), so check a real day with a round trip: `new Date(ms).toISOString().slice(0, 10) === value`; the round trip accepts year `0000`, so reject that prefix separately (`h10`). The date range compares ISO strings, and the payroll range uses `new Decimal(value)` with `gt` and `lte`.
- Java: `Pattern.matcher(value).matches()` is a whole-string match; write `[0-9]` explicitly. `LocalDate.parse` is strict and throws `DateTimeParseException` for 30 February, so catch it as `invalid`; it accepts year 0, so test `getYear() < 1` too (`h10`). The payroll range uses `signum() > 0` and `compareTo`. Keep duplicate keys in a `HashSet<List<String>>` of `List.of(a, b, c)`.
- Kotlin: `Regex("[0-9]{4}").matches(value)` is a whole-string match, `runCatching { LocalDate.parse(value) }.getOrNull()` turns the strict parse into a nullable (with `day.year < 1` rejected as in Java), `hashSetOf<Triple<String, String, String>>()` holds the keys, and `buildList { ... }` collects the errors.
- Go: `regexp.MustCompile` with `^...$` anchors, and `[0-9]` written out (RE2's `\d` is ASCII-only, but the explicit class states the intent). `time.Parse(time.DateOnly, value)` is strict about 30 February but accepts year 0, so the reference tests `Year() < 1` and reports `invalid`, as the other languages do. The payroll range uses `shopspring/decimal` (`IsPositive`, `GreaterThan`), which parses the longest allowed values. Duplicate keys are a `map` keyed by a small struct, since slices cannot be map keys.
- Rust: the standard library has no regex engine, so each shape is a short byte check. `NaiveDate::from_ymd_opt` rejects 30 February and accepts year 0, so the reference tests `year >= 1` separately. The payroll range compares digit strings (leading zeros trimmed, then length, then text), because `rust_decimal` holds at most 28 digits and a payroll value may have 40.
