# Debug: Sorted Report Rows

## Statement

A nightly job writes the sales report's top section. `regions[i]` had sales of `totalsCents[i]` cents, and `topRegions` should return the first `limit` rows, each as `"<region>: <total>"`:

1. Larger totals come first. A total can be negative, when refunds outweigh sales.
2. Regions with equal totals are listed by name, in ascending order compared with `<`.

The function looks finished, and its author's two test files pass. Find the bugs and fix them.

### Bug report

> **Title:** The sales report puts numbers next to the wrong regions
>
> Tonight's report says `west: 900`, and the sales team says `west` had a slow month with 120. The list of numbers looks plausible on its own, but they don't seem to belong to the names beside them. It also seems wrong in the months when one region crosses 1000: that total appeared below smaller ones. Reports with only three-digit totals, listed from the biggest down, always looked fine.

## Input

- `regions`: distinct region names
- `totalsCents`: `totalsCents[i]` is the total of `regions[i]`
- `limit`: how many rows to return

## Output

At most `limit` rows, as strings, in the order above.

## Examples

### Example 1

<!-- case: ex1 -->

The regions are already listed from the largest total down, and all three totals have the same number of digits. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

Only the top row is asked for. This case passes as shipped too.

## Constraints

- `1 <= regions.length == totalsCents.length <= 1000`
- `-10^9 <= totalsCents[i] <= 10^9`
- `0 <= limit <= 1000`; a `limit` above the number of regions returns every row.
- Region names are 1 to 12 lowercase ASCII letters.

## Follow-ups

- The caller also keeps using `totalsCents` after this function returns. What did it see before your fix?
- How would you have this report's sort pinned by a test that fails the day someone removes the comparator?

## Hints

### Hint 1

Call the function with `["a", "b"]` and `[5, 1000]`, and read what comes back. Which row is wrong, and in how many ways?

### Hint 2

What does `.sort()` compare when you give it no function? Try `[1000, 5, 90].sort()` in a Node prompt.

### Hint 3

Log `totalsCents` before and after the sort. Is the array the same one, and what does `indexOf` search afterwards?

### Hint 4

When two regions have the same total, what does `indexOf` return for the second one? Think about sorting positions instead of values.
