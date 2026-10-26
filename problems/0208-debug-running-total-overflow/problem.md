# Debug: Running Total Overflow

## Statement

An invoicing service prices orders in cents. Line `i` of an invoice sells `quantities[i]` units at `unitPrices[i]` cents each. The function `invoiceTotal` you start from should return the invoice total in cents: the sum over all lines of `unitPrices[i] * quantities[i]`, exactly.

The return type is already `long`, and the code passes every small invoice. It fails on others. Find out why and fix it so every total within the constraints is exact.

### Bug report

> **Title:** Wholesale invoices show negative or tiny totals
>
> Finance flagged three invoices from the new wholesale channel. One shows a total of `-$21,474,836.48`. One shows `$12,157,521.92` for an order of 100,000 units at $10,000.00 each, which should be a billion dollars. The worst one, about $42.9 million of goods, was billed at five cents and nobody noticed until the audit. Retail invoices are fine. A developer already changed the method's return type from `int` to `long` last quarter "to fix big totals"; the complaints continued.

## Input

- `unitPrices`: the price of one unit on each line, in cents
- `quantities`: the number of units on each line; `quantities[i]` belongs to `unitPrices[i]`

## Output

The exact total in cents, as a `long`.

## Examples

### Example 1

<!-- case: ex1 -->

499 * 3 + 1250 * 2 + 99 * 10 = 1497 + 2500 + 990 = 4987 cents, or $49.87. Small invoices like this pass as shipped.

### Example 2

<!-- case: ex2 -->

250000 * 40 + 1 * 7 = 10,000,007 cents. Still far below 2^31 - 1 = 2,147,483,647, so this passes too.

## Constraints

- `0 <= unitPrices.length == quantities.length <= 1000`
- `0 <= unitPrices[i] <= 10^6`
- `0 <= quantities[i] <= 10^6`
- The exact total is at most 10^15, so it always fits in a `long`.

## Follow-ups

- How would you make the code fail loudly, instead of silently, if a total ever exceeded the range of `long`?
- Money is often stored as `BigDecimal`. What would that cost here, and what would it buy?

## Hints

### Hint 1

Every failing invoice in the ticket is large. Try to find the smallest total that comes out wrong. Is there a sharp threshold?

### Hint 2

Compare `-21,474,836.48` dollars with `2^31` cents. What happens to an `int` that grows past `2,147,483,647`?

### Hint 3

Changing the return type widened the result after the arithmetic had already happened. In which type is each multiplication and each addition computed?

### Hint 4

`(long) total` at the end cannot recover bits that were lost earlier. Making the accumulator a `long` is not enough on its own either: test a single line of 100,000 units at 1,000,000 cents.
