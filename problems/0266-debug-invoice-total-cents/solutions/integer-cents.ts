const CENTS_PER_UNIT = 100;
const BASIS_POINTS = 10000;

/** Reads the digits, so no multiplication has a chance to go wrong: "5.5" is 550. */
function toCents(price: string): number {
  const [whole, fraction = ""] = price.split(".");
  return Number(whole) * CENTS_PER_UNIT + Number(fraction.padEnd(2, "0"));
}

/** `dividend / divisor`, a half rounding up, without leaving the whole numbers. */
function dividedHalfUp(dividend: number, divisor: number): number {
  return Math.floor((2 * dividend + divisor) / (2 * divisor));
}

export function invoiceTotalCents(
  unitPrices: string[],
  quantities: number[],
  taxBasisPoints: number,
): number {
  let subtotal = 0;
  unitPrices.forEach((price, line) => {
    subtotal += toCents(price) * quantities[line];
  });
  return subtotal + dividedHalfUp(subtotal * taxBasisPoints, BASIS_POINTS);
}
