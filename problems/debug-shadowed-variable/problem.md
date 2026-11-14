# Debug: Shadowed Variable

## Statement

A web shop computes what a customer pays, in cents. The function `checkoutTotal` you start from should add up `prices` and subtract the discount of `coupon`:

- An empty `coupon` gives no discount.
- `PCT<n>`, with `1 <= n <= 100`, takes `n` percent off the subtotal, rounded down to a whole cent.
- `OFF<n>`, with `n >= 1`, takes `n` cents off.
- `<n>` is a base-10 number; leading zeros are allowed, so `PCT015` is 15 percent.
- The discount never exceeds the subtotal, so the total is never negative.
- Any other coupon is invalid, and the order is rejected: return `-1`.

The code compiles, `go vet` is silent, and the tests for `couponDiscount` pass. Customers still pay the wrong amount. Find out why and fix it.

### Bug report

> **Title:** Valid coupons are accepted but never applied
>
> Since the checkout refactor, customers who enter a valid coupon pay full price. The coupon box shows "Coupon applied", because the page only checks that the order was not rejected, and invalid coupons are still rejected as before. Support refunded about 400 orders last week. The refactor moved the coupon parsing into `couponDiscount`, whose unit tests all pass.

## Input

- `prices`: the price of each item in the cart, in cents
- `coupon`: the code the customer entered, or an empty string

## Output

The amount to pay in cents, or `-1` when the coupon is invalid.

## Examples

### Example 1

<!-- case: ex1 -->

No coupon: 1999 + 500 + 250 = 2749 cents. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

`SAVE10` is not a coupon the shop knows, so the order is rejected. This case passes too.

## Constraints

- `0 <= prices.length <= 1000`
- `0 <= prices[i] <= 10^6`
- `coupon` is empty or has 1 to 12 characters, each an uppercase letter or a digit.

## Follow-ups

- Restructure `checkoutTotal` so that no `:=` appears inside the `if` block at all. Which version is clearest?
- Which linters report a shadowed variable, and why is the check off by default?

## Hints

### Hint 1

Run a valid coupon such as `PCT10`. Add a print of `discount` inside the `if` block, after the clamp, and another right before the `return`.

### Hint 2

The two prints disagree. How many variables named `discount` does `checkoutTotal` have?

### Hint 3

`:=` declares every name on its left that is not already declared *in the same scope*. The `if` block is a new scope.

### Hint 4

Declare `err` with `var err error` before the call and use `=`, so the call assigns the `discount` declared outside the block.
