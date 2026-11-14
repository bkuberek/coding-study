interface History {
  timestamps: number[];
  values: string[];
}

export class TimeMap {
  private readonly history = new Map<string, History>();

  constructor() {}

  set(key: string, value: string, timestamp: number): void {
    let entries = this.history.get(key);
    if (entries === undefined) {
      entries = { timestamps: [], values: [] };
      this.history.set(key, entries);
    }
    entries.timestamps.push(timestamp);
    entries.values.push(value);
  }

  get(key: string, timestamp: number): string {
    const entries = this.history.get(key);
    if (entries === undefined) {
      return "";
    }
    // Find how many writes happened at or before timestamp (upper bound).
    const times = entries.timestamps;
    let low = 0;
    let high = times.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (times[middle] <= timestamp) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low > 0 ? entries.values[low - 1] : "";
  }
}
