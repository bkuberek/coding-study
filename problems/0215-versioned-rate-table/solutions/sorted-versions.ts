import { Decimal } from "#support";

interface Version {
  id: number;
  rates: Map<string, Decimal>;
}

const NOT_FOUND = new Decimal(-1);

export class RateTable {
  // Parallel arrays sorted by effective date (ISO strings sort chronologically);
  // equal dates stay in publish order.
  private readonly dates: string[] = [];
  private readonly versions: Version[] = [];
  private published = 0;

  constructor() {}

  publish(effectiveDate: string, classCodes: string[], rates: Decimal[]): void {
    this.published += 1;
    const slot = this.versionsOnOrBefore(effectiveDate);
    // A fresh map, so a published version never changes afterwards.
    const table = new Map<string, Decimal>();
    classCodes.forEach((code, i) => table.set(code, rates[i]));
    this.dates.splice(slot, 0, effectiveDate);
    this.versions.splice(slot, 0, { id: this.published, rates: table });
  }

  rateAsOf(onDate: string, classCode: string): Decimal {
    const slot = this.versionsOnOrBefore(onDate);
    if (slot === 0) {
      return NOT_FOUND;
    }
    return this.versions[slot - 1].rates.get(classCode) ?? NOT_FOUND;
  }

  versionAsOf(onDate: string): number {
    const slot = this.versionsOnOrBefore(onDate);
    return slot > 0 ? this.versions[slot - 1].id : -1;
  }

  // Number of versions effective on or before the day (upper bound).
  private versionsOnOrBefore(day: string): number {
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
