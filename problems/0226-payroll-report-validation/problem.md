# Payroll Report Validation

## Statement

Each month a contractor uploads its payroll report as rows of text, one row per class code: `[contractorId, classCode, payroll, periodStart]`. Before the report is accepted, every problem in it must be listed at once, so the contractor can fix everything in one go. Check every row against the rules below, never stopping at the first error, and return every error as the text `"<row>:<field>:<reason>"`, where `<row>` is the 0-based row number.

Fields are `contractorId`, `classCode`, `payroll` and `periodStart`, or `row` for an error about the row as a whole. Reasons are `missing`, `invalid`, `out-of-range`, `duplicate` and `column-count`. "Digit" means the ASCII digits `0` to `9` only.

Rules, applied to every row:

1. A row without exactly four values gets only `<row>:row:column-count`, and is skipped by every other rule, including the duplicate rule.
2. A value that is the empty text is `missing`. Values are never trimmed: `" 5"` is `invalid`, not `5`.
3. `contractorId` is 1 to 20 characters, each one of `a` to `z`, `0` to `9` or `-`; otherwise it is `invalid`.
4. `classCode` is exactly four digits; otherwise it is `invalid`.
5. `payroll` is one or more digits, optionally followed by a point and one or two digits; otherwise it is `invalid`. A well-formed payroll is `out-of-range` unless it is greater than 0 and at most 1,000,000,000.
6. `periodStart` has the form `YYYY-MM-DD` (four, two and two digits) and names a real calendar day in the years 0001 to 9999; otherwise it is `invalid`. Year `0000` is therefore `invalid`. A real day is `out-of-range` unless it lies between `2000-01-01` and `2099-12-31`.
7. A row is a `duplicate` when its `contractorId`, `classCode` and `periodStart` all passed their rules, and an earlier row whose same three fields passed has the same three values. Add `<row>:row:duplicate`. The payroll does not matter.

## Input

- `rows`: the report; each row is a list of text values

## Output

The errors in row order (by number, so row 10 comes after row 9), then in column order within a row, with a row's `duplicate` error last. An empty list when the report is clean.

## Examples

### Example 1

<!-- case: ex1 -->

The first row is clean. In the second row, `C-101` has an uppercase letter, `54O3` has a letter O instead of a zero, `12.345` has three fractional digits, and 30 February is not a day. All four fields fail, in column order.

### Example 2

<!-- case: ex2 -->

Row 1 repeats the contractor, class code and period of row 0, so it is a duplicate, even though its payroll differs. Row 2 has the same contractor and class code but another period, so it is not.

### Example 3

<!-- case: ex3 -->

Row 0 has three values and row 2 has five, so both get a column-count error and nothing else. Row 1 has four empty values, so each field is missing.

## Constraints

- `0 <= rows.length <= 10^4`, and a row has 0 to 10 values.
- Each value has 0 to 40 characters, any of which may be outside ASCII.

## Follow-ups

- Stop after the first 100 errors.
- Warnings as well as errors, for example a payroll ten times last month's.
- Check class codes against a table of valid codes.
- Name the earlier row in a duplicate error.

## Hints

### Hint 1

Write one small check per field that returns a reason or nothing.

### Hint 2

Check a date's shape before you ask a date library: libraries accept other shapes, or roll an invalid day over into the next month.

### Hint 3

For duplicates, keep a set of keys from rows whose key fields passed.
