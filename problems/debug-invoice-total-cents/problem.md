# Debug: Invoice Total Cents

## Statement

A billing job works out what an invoice comes to. `unitPrices[i]` is the price of line `i` as a decimal string, the way the pricing service sends it, and `quantities[i]` is how many were bought. `invoiceTotalCents` returns the total in whole cents:

1. The subtotal is the sum over the lines of price times quantity.
2. The tax is the subtotal times `taxBasisPoints / 10000`, so 725 means 7.25%. It is rounded to a whole cent, once, on the subtotal, and an exact half rounds up.
3. The total is the subtotal plus the tax.

The rates and prices here are invented; this is an exercise, not tax advice. The function looks right, and round prices come out right. Find the bug and fix it.

### Bug report

> **Title:** Customers are charged a cent less than the page says
>
> A customer bought one item at 19.99, with no tax, and the invoice says 1998 cents. Finance found a few hundred like it this quarter, each off by one cent. A developer changed the last line to round instead of truncate on a branch, and that invoice came out right, but finance says some totals with tax are still one cent off against their spreadsheet.

## Input

- `unitPrices`: prices as decimal strings, such as `"19.99"`, `"5.5"` or `"5"`
- `quantities`: `quantities[i]` is the quantity of line `i`
- `taxBasisPoints`: the tax rate in hundredths of a percent

## Output

The total in whole cents.

## Examples

### Example 1

<!-- case: ex1 -->

Two items at 10.00 and no tax. Round prices survive the arithmetic, so this case passes as shipped.

### Example 2

<!-- case: ex2 -->

Four items at 12.50 make 5000 cents, and 8% of that is exactly 400. This case passes as shipped too.

## Constraints

- `0 <= unitPrices.length == quantities.length <= 1000`
- A price is digits, optionally followed by a point and one or two digits.
- `0 <= quantities[i] <= 10000`
- `0 <= taxBasisPoints <= 10000`
- Every value at every step stays far below `2^53`.

## Follow-ups

- Where would you store money: in integer cents, or in a decimal type in the database? What changes if a price can have a third decimal place?
- Finance rounds tax once on the subtotal. Another team rounds per line. Why can't both totals be right, and who decides?

## Hints

### Hint 1

Try `19.99 * 100` in a Node prompt. Then try `4.35 * 100` and `1.15 * 100`.

### Hint 2

Rounding the final number fixes the example in the report. Why is that not enough? Take a price of 1.15 and a tax of 10%, and work out the exact tax by hand.

### Hint 3

If the numbers were whole cents from the start, which of the operations here could ever produce a fraction?

### Hint 4

To read `"19.99"` as 1999 without a multiplication by 100 going wrong, you can split it at the point. Watch out for `"5.5"`.
