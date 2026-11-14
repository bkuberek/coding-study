# Debug: Invoice Total Cents: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| integer-cents | optimal | O(n) | O(1) | default answer: money is whole cents from the first line to the last |

## Approach: integer-cents (Integer cents from the first line)

### Intuition

A JavaScript `number` is an IEEE 754 double, which stores binary fractions. 19.99 has no exact binary form, so the nearest double is a little under it, and `19.99 * 100` is `1998.9999999999998`. `Math.trunc` then drops the .9999, and a cent goes with it.

Changing `trunc` to `round` is the tempting fix, and it does fix that invoice. But it only hides the first error, because the sum still lives in floats when it reaches a real rounding decision. When the exact answer ends in .5 of a cent, a float can land just under it. A price of 1.15 with 10% tax is exactly 115 + 11.5, which should round to 127, and in floats it comes out at `126.49999999999999`, which rounds to 126.

So the fix isn't a better rounding call. It is to stop having fractions: read each price as whole cents, multiply by whole quantities, and do the one division in whole-number arithmetic, at the end.

### Say it out loud

"This is floating point: 19.99 isn't representable in binary, so multiplying by 100 gives 1998.9999... Rounding at the end hides that case, but the half-cent cases are still wrong, because the error is there before you round. I'd represent money in integer cents, parse the string without going through a float, and round exactly once, in integer arithmetic, where the rule says to."

### Debugging approach

1. **Reproduce.** `invoiceTotalCents(["19.99"], [1], 0)` is 1998.
2. **Find where it stops being exact.** Log `19.99 * 100` on its own: the error is there before `trunc` ever runs.
3. **Test the tempting fix against a real rounding decision.** Find a case whose exact tax ends in .5: `1.15` at 10% (`h3`). `Math.round` gets 126, and the exact answer is 127.
4. **Check the other half-fixes.** `toFixed(2)` also rounds the float (`h5`). `Math.round(Number(price) * 100)` per line is right for the prices, and then a truncating tax is wrong (`h7`). A per-line tax misses `h9`. Removing the dot from the string misses `"5.5"` (`h10`).

### Algorithm

1. Split each price at the point, and read the whole part and the fraction, padded to two digits, as whole numbers.
2. Add up `cents * quantity` as the subtotal.
3. Work out the tax with `floor((2 * subtotal * bps + 10000) / 20000)`, which is `subtotal * bps / 10000` with a half rounding up.
4. Return their sum.

### Correctness

Every price becomes the exact whole number of cents it names, because no value passes through a binary fraction. Sums and products of whole numbers below `2^53` are exact in a double. In the one division, `2 * subtotal * bps + 10000` is an exact whole number, and adding half the divisor then flooring is the definition of rounding half up for positive numbers. The quotient of two whole numbers below `2^53` can't round across a whole number when the divisor is this small, so `Math.floor` gets the right one.

### Complexity

- Time: O(n) — one pass over the lines; parsing each short price is O(1).
- Space: O(1) — a running subtotal.

### Trade-offs

`Math.round(Number(price) * 100)` also reads a two-decimal price correctly, because the error is far below half a cent, and many codebases do this. Splitting the string makes the exactness obvious, and it doesn't rest on that argument. A decimal library (or `BigInt` cents) removes the size limit too, at the cost of a dependency or of a different number type everywhere. For a sum that fits well under `2^53`, a plain `number` of cents is what most services use.

### Pitfalls and edge cases

- The general trap: never do money in binary floats. `0.1 + 0.2` is `0.30000000000000004`, and it only sometimes shows.
- Rounding can't repair a float after the fact, since the value may already sit on the wrong side of a half.
- `toFixed` rounds the double it was given, which may be under the half you wrote: `(1.005).toFixed(2)` is `"1.00"`.
- `Number("19.99".replace(".", ""))` reads 1999, and it reads `"5.5"` as 55 and `"5"` as 5.
- `Number(fraction)` without padding reads `"5.5"` as 5 cents, not 50.
- Round once, at the place the rule says. Rounding per line and rounding per invoice both exist, and they give different totals (`h9`).
- `Math.round` rounds a half up, toward positive infinity, so `Math.round(-2.5)` is -2. That doesn't matter here, but it does for refunds.

### Prevention

- Name money with its unit: `amountCents`, never `amount` or `price`. A `number` called `totalCents` that isn't whole is then visibly wrong.
- Accept money as a string or as integer cents at the API edge, never as a JSON number with decimals.
- Test with prices known to misbehave (19.99, 4.35, 1.15) and with taxes that land on an exact half cent. Round numbers hide all of this.

### Language notes

TypeScript has a single `number` type, so the compiler can't tell cents from dollars: only the name can. `Math.trunc`, `Math.floor` and `Math.round` all take the double they are given, and none of them can know the exact value it came from.
