import { Decimal } from "#support";

const MILLIS_PER_DAY = 86_400_000;

function utcMillis(day: string): number {
  const [year, month, dayOfMonth] = day.split("-").map(Number);
  return Date.UTC(year, month - 1, dayOfMonth);
}

export class DecimalDates {
  normalized(value: Decimal): Decimal {
    return value;
  }

  add(left: Decimal, right: Decimal): Decimal {
    return left.plus(right);
  }

  total(values: Decimal[]): Decimal {
    return values.reduce((sum, value) => sum.plus(value), new Decimal(0));
  }

  roundHalfUp(value: Decimal): Decimal {
    return value.round(2, "HALF_UP");
  }

  roundHalfEven(value: Decimal): Decimal {
    return value.round(2, "HALF_EVEN");
  }

  prorate(premium: Decimal, days: number, totalDays: number): Decimal {
    return premium
      .times(new Decimal(days))
      .div(new Decimal(totalDays), 2, "HALF_UP");
  }

  addDays(day: string, days: number): string {
    const moved = new Date(utcMillis(day) + days * MILLIS_PER_DAY);
    return moved.toISOString().slice(0, 10);
  }

  daysBetween(start: string, end: string): number {
    return Math.round((utcMillis(end) - utcMillis(start)) / MILLIS_PER_DAY);
  }
}
