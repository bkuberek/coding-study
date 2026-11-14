import { Decimal } from "#support";

export function calculateTax(brackets: number[][], income: number): Decimal {
  let cents = 0; // tax in hundredths of a unit: every rate is a whole percent
  let bracket = 0;
  for (let unit = 0; unit < income; unit++) {
    // Unit number unit covers income from unit to unit + 1.
    while (brackets[bracket][0] <= unit) {
      bracket++;
    }
    cents += brackets[bracket][1];
  }
  return new Decimal(BigInt(cents), 2);
}
