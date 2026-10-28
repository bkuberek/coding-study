import { Decimal, type IsoDate } from "#support";

const MILLIS_PER_DAY = 86_400_000;
const OUTSIDE_TERM = new Decimal(-1);

// Date-only ISO strings parse as UTC, so the difference is a whole number of days.
function daysBetween(from: IsoDate, to: IsoDate): number {
  return (Date.parse(to) - Date.parse(from)) / MILLIS_PER_DAY;
}

export function unearnedPremium(
  termPremium: Decimal,
  termStart: IsoDate,
  termEnd: IsoDate,
  changeDate: IsoDate,
): Decimal {
  if (changeDate < termStart || changeDate > termEnd) {
    return OUTSIDE_TERM;
  }
  const remaining = new Decimal(daysBetween(changeDate, termEnd));
  const termDays = new Decimal(daysBetween(termStart, termEnd));
  return termPremium.times(remaining).div(termDays, 2, "HALF_UP");
}
