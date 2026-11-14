import { Decimal, type IsoDate } from "#support";

const NO_EARNED_PREMIUM = new Decimal(-1);

// Periods are calendar-aligned blocks of months counted from January of year 0.
function periodIndex(day: IsoDate, periodMonths: number): number {
  const months = Number(day.slice(0, 4)) * 12 + Number(day.slice(5, 7)) - 1;
  return Math.floor(months / periodMonths);
}

function sumByPeriod(
  dates: IsoDate[],
  amounts: Decimal[],
  periodMonths: number,
  first: number,
  count: number,
): Decimal[] {
  const totals = Array.from({ length: count }, () => new Decimal(0));
  dates.forEach((day, i) => {
    const slot = periodIndex(day, periodMonths) - first;
    if (slot >= 0 && slot < count) {
      totals[slot] = totals[slot].plus(amounts[i]);
    }
  });
  return totals;
}

export function lossRatios(
  earnedDates: IsoDate[],
  earnedAmounts: Decimal[],
  lossDates: IsoDate[],
  lossAmounts: Decimal[],
  fromDate: IsoDate,
  toDate: IsoDate,
  periodMonths: number,
): Decimal[] {
  const first = periodIndex(fromDate, periodMonths);
  const count = periodIndex(toDate, periodMonths) - first + 1;
  const earned = sumByPeriod(earnedDates, earnedAmounts, periodMonths, first, count);
  const losses = sumByPeriod(lossDates, lossAmounts, periodMonths, first, count);
  return earned.map((premium, slot) =>
    premium.eq(new Decimal(0)) ? NO_EARNED_PREMIUM : losses[slot].div(premium, 4, "HALF_UP"),
  );
}
