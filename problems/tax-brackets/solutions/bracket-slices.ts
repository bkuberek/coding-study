import { Decimal } from "#support";

export function calculateTax(brackets: number[][], income: number): Decimal {
  let cents = 0; // tax in hundredths of a unit: every rate is a whole percent
  let lower = 0;
  for (const [upper, percent] of brackets) {
    if (lower >= income) {
      break;
    }
    cents += (Math.min(upper, income) - lower) * percent;
    lower = upper;
  }
  return new Decimal(BigInt(cents), 2);
}
