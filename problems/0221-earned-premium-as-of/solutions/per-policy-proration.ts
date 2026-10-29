import { Decimal, type IsoDate } from "#support";

const MILLIS_PER_DAY = 86_400_000;

// Date-only ISO strings parse as UTC, so the difference is a whole number of days.
function daysBetween(from: IsoDate, to: IsoDate): number {
  return (Date.parse(to) - Date.parse(from)) / MILLIS_PER_DAY;
}

export function earnedPremium(
  premiums: Decimal[],
  terms: IsoDate[][],
  valuationDate: IsoDate,
): Decimal {
  let total = new Decimal(0);
  premiums.forEach((premium, i) => {
    const [start, end] = terms[i];
    const termDays = daysBetween(start, end);
    const earnedDays = Math.min(Math.max(daysBetween(start, valuationDate), 0), termDays);
    // Each policy is rounded to cents on its own; the book total is the sum of rounded amounts.
    total = total.plus(premium.times(new Decimal(earnedDays)).div(new Decimal(termDays), 2, "HALF_UP"));
  });
  return total;
}
