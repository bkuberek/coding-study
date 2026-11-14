# Rate Change Impact

## Statement

When a new version of a class-rate table is published, underwriters want to see what moved. Compare the old table with the new one and report each class code whose rate changed, with the change in percent; each code that is new; and each code that was dropped.

A rate that is equal by value (`12.50` and `12.5`) has not changed, and is not reported. The percent change is `(new - old) / old * 100`, rounded to two decimal places, half up, and written with exactly two digits after the point: `"4.80"`, `"-10.00"`, `"0.00"`. A change that rounds to zero is written `"0.00"`, never `"-0.00"`.

List the changed codes from the largest increase to the largest decrease (by the rounded percent, ties by code), then the added codes, then the removed codes, each of these two groups in code order. Codes compare character by character.

## Input

- `oldCodes`, `oldRates`: the old table; `oldCodes[i]` had rate `oldRates[i]`
- `newCodes`, `newRates`: the new table; `newCodes[i]` has rate `newRates[i]`

## Output

Rows `[code, status, percent]` where `status` is `changed`, `added` or `removed`. The percent is text with two fractional digits for a changed code, and the empty text `""` for an added or removed code.

## Examples

### Example 1

<!-- case: ex1 -->

Code `5403` goes from 12.50 to 13.10: +4.80 percent. Code `5645` goes from 18.00 to 16.20: -10.00 percent. The increase comes first. `9102` exists only in the new table and `8810` only in the old one.

### Example 2

<!-- case: ex2 -->

`5403` is 12.50 in the old table and 12.5 in the new one: equal by value, so it is not reported. `5606` goes from 20 to 21 and `5645` from 8 to 8.40, both +5.00 percent, so they tie and appear in code order.

### Example 3

<!-- case: ex3 -->

The old table is empty, so every code in the new table is added, in code order.

## Constraints

- `0 <= oldCodes.length == oldRates.length <= 10^4`, and the same for the new table.
- Codes are distinct within a table, and 1 to 8 characters of `[0-9A-Za-z]`.
- `0 < rate <= 10^4`, with at most 4 fractional digits.

## Follow-ups

- The premium impact per insured: rate change times exposure.
- Flag changes beyond a cap, such as 25 percent in either direction.
- Compare more than two versions (see `versioned-rate-table`).
- Both tables are already sorted by code: a merge needs O(n) time and O(1) extra space.

## Hints

### Hint 1

Index each table by code.

### Hint 2

Round first, then sort by the rounded number, not by its text.

### Hint 3

Format the percent with a fixed scale of two.
