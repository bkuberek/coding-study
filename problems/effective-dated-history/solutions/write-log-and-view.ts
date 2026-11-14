import type { IsoDate } from "#support";

// Number of items that are <= target in a sorted array (upper bound).
function countAtOrBefore<T extends string | number>(items: T[], target: T): number {
  let low = 0;
  let high = items.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (items[middle] <= target) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}

interface Write {
  effectiveDate: IsoDate;
  value: string;
}

class FieldHistory {
  private readonly writeTimes: number[] = []; // every write, in timestamp order
  private readonly writes: Write[] = [];
  private readonly dates: IsoDate[] = []; // current view: one value per effective date, sorted
  private readonly values: string[] = [];

  write(timestamp: number, effectiveDate: IsoDate, value: string): void {
    this.writeTimes.push(timestamp);
    this.writes.push({ effectiveDate, value });
    const after = countAtOrBefore(this.dates, effectiveDate);
    if (after > 0 && this.dates[after - 1] === effectiveDate) {
      this.values[after - 1] = value; // a correction replaces the value for that date
    } else {
      this.dates.splice(after, 0, effectiveDate);
      this.values.splice(after, 0, value);
    }
  }

  current(onDate: IsoDate): string {
    const after = countAtOrBefore(this.dates, onDate);
    return after > 0 ? this.values[after - 1] : "";
  }

  asKnown(onDate: IsoDate, knownAt: number): string {
    let bestDate: IsoDate | null = null;
    let bestValue = "";
    const known = countAtOrBefore(this.writeTimes, knownAt); // writes made at or before knownAt
    for (let i = 0; i < known; i += 1) {
      const { effectiveDate, value } = this.writes[i];
      // >= lets a later write for the same date replace an earlier one
      if (effectiveDate <= onDate && (bestDate === null || effectiveDate >= bestDate)) {
        bestDate = effectiveDate;
        bestValue = value;
      }
    }
    return bestValue;
  }
}

export class RecordHistory {
  private readonly records = new Map<string, Map<string, FieldHistory>>();

  constructor() {}

  setValue(timestamp: number, recordId: string, field: string, effectiveDate: IsoDate, value: string): void {
    let fields = this.records.get(recordId);
    if (fields === undefined) {
      fields = new Map();
      this.records.set(recordId, fields);
    }
    let history = fields.get(field);
    if (history === undefined) {
      history = new FieldHistory();
      fields.set(field, history);
    }
    history.write(timestamp, effectiveDate, value);
  }

  getValue(timestamp: number, recordId: string, field: string, onDate: IsoDate): string {
    return this.records.get(recordId)?.get(field)?.current(onDate) ?? "";
  }

  snapshot(timestamp: number, recordId: string, onDate: IsoDate): string[] {
    return this.snapshotWith(recordId, (history) => history.current(onDate));
  }

  getValueAsKnown(
    timestamp: number,
    recordId: string,
    field: string,
    onDate: IsoDate,
    knownAt: number,
  ): string {
    return this.records.get(recordId)?.get(field)?.asKnown(onDate, knownAt) ?? "";
  }

  snapshotAsKnown(timestamp: number, recordId: string, onDate: IsoDate, knownAt: number): string[] {
    return this.snapshotWith(recordId, (history) => history.asKnown(onDate, knownAt));
  }

  private snapshotWith(recordId: string, read: (history: FieldHistory) => string): string[] {
    const fields = this.records.get(recordId);
    if (fields === undefined) {
      return [];
    }
    const entries: string[] = [];
    // Default sort() orders by code unit, which is character-code order for these ASCII names.
    for (const field of [...fields.keys()].sort()) {
      const value = read(fields.get(field)!);
      if (value !== "") {
        entries.push(`${field}=${value}`);
      }
    }
    return entries;
  }
}
