import { Decimal, type IsoDate } from "#support";

const MILLIS_PER_DAY = 86_400_000;
const OUTSIDE_TERM = new Decimal(-1);

// Date-only ISO strings parse as UTC, so the difference is a whole number of days.
function daysBetween(from: IsoDate, to: IsoDate): number {
  return (Date.parse(to) - Date.parse(from)) / MILLIS_PER_DAY;
}

export class EndorsedPolicy {
  private readonly termStart: IsoDate;
  private readonly termEnd: IsoDate;
  private readonly termDays: number;
  // Parallel arrays sorted by date: the full-term premium in force from each date on.
  private readonly dates: IsoDate[];
  private readonly premiums: Decimal[];

  constructor(termStart: IsoDate, termEnd: IsoDate, fullTermPremium: Decimal) {
    this.termStart = termStart;
    this.termEnd = termEnd;
    this.termDays = daysBetween(termStart, termEnd);
    this.dates = [termStart];
    this.premiums = [fullTermPremium];
  }

  endorse(effectiveDate: IsoDate, fullTermPremium: Decimal): boolean {
    if (effectiveDate < this.termStart || effectiveDate >= this.termEnd) {
      return false;
    }
    const slot = this.firstNotBefore(effectiveDate);
    if (slot < this.dates.length && this.dates[slot] === effectiveDate) {
      this.premiums[slot] = fullTermPremium; // same date: the later endorsement corrects it
    } else {
      this.dates.splice(slot, 0, effectiveDate);
      this.premiums.splice(slot, 0, fullTermPremium);
    }
    return true;
  }

  premiumOn(onDate: IsoDate): Decimal {
    if (onDate < this.termStart || onDate >= this.termEnd) {
      return OUTSIDE_TERM;
    }
    // The greatest effective date on or before onDate: one before the first date after it.
    return this.premiums[this.firstAfter(onDate) - 1];
  }

  writtenPremium(): Decimal {
    return this.earnedPremium(this.termEnd);
  }

  earnedPremium(asOfDate: IsoDate): Decimal {
    let cutoff = asOfDate < this.termStart ? this.termStart : asOfDate;
    if (cutoff > this.termEnd) {
      cutoff = this.termEnd;
    }
    let weighted = new Decimal(0); // sum of premium * days over the segments before the cutoff, exact
    for (let segment = 0; segment < this.dates.length; segment += 1) {
      const start = this.dates[segment];
      if (start >= cutoff) {
        break;
      }
      const end = segment + 1 < this.dates.length ? this.dates[segment + 1] : this.termEnd;
      const stop = end < cutoff ? end : cutoff;
      weighted = weighted.plus(this.premiums[segment].times(new Decimal(daysBetween(start, stop))));
    }
    return weighted.div(new Decimal(this.termDays), 2, "HALF_UP");
  }

  // Index of the first date that is not before the day (lower bound).
  private firstNotBefore(day: IsoDate): number {
    let low = 0;
    let high = this.dates.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.dates[middle] < day) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  }

  // Index of the first date that is after the day (upper bound).
  private firstAfter(day: IsoDate): number {
    let low = 0;
    let high = this.dates.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.dates[middle] <= day) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  }
}
