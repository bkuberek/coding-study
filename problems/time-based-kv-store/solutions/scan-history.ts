export class TimeMap {
  private readonly history = new Map<string, { timestamp: number; value: string }[]>();

  constructor() {}

  set(key: string, value: string, timestamp: number): void {
    let entries = this.history.get(key);
    if (entries === undefined) {
      entries = [];
      this.history.set(key, entries);
    }
    entries.push({ timestamp, value });
  }

  get(key: string, timestamp: number): string {
    const entries = this.history.get(key) ?? [];
    for (let i = entries.length - 1; i >= 0; i--) {
      if (entries[i].timestamp <= timestamp) {
        return entries[i].value;
      }
    }
    return "";
  }
}
