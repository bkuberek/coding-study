import { Decimal, type IsoDate } from "#support";

function pad(value: number, width: number): string {
  return String(value).padStart(width, "0");
}

export function installmentSchedule(
  premium: Decimal,
  installmentCount: number,
  firstDueDate: IsoDate,
): string[][] {
  if (installmentCount === 0) {
    return [];
  }
  // Exact: the premium has at most two fractional digits, so the result has scale 0.
  const cents = premium.movePointRight(2).unscaled;
  const count = BigInt(installmentCount);
  const base = cents / count;
  const leftover = Number(cents % count);
  const [anchorYear, anchorMonth, anchorDay] = firstDueDate.split("-").map(Number);
  const schedule: string[][] = [];
  for (let number = 0; number < installmentCount; number += 1) {
    // Leftover cents go to the first installments.
    const amount = number < leftover ? base + 1n : base;
    // Counted from the anchor, never from the previous due date.
    const monthIndex = anchorMonth - 1 + number;
    const year = anchorYear + Math.floor(monthIndex / 12);
    const month = monthIndex % 12;
    // Day 0 of the next month is the last day of this one. Date.UTC(y, m, 31) would roll over.
    const monthLength = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const day = Math.min(anchorDay, monthLength);
    schedule.push([`${pad(year, 4)}-${pad(month + 1, 2)}-${pad(day, 2)}`, new Decimal(amount, 2).toString()]);
  }
  return schedule;
}
