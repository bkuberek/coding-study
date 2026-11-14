// One write to a field: a value (null for a deletion), from `since` until `expiresAt`.
interface Version {
  readonly since: number;
  readonly value: string | null;
  readonly expiresAt: number | null;
}

// Every version of one field, oldest first; timestamps arrive in increasing order.
class FieldHistory {
  private readonly versions: Version[] = [];

  record(version: Version): void {
    this.versions.push(version);
  }

  valueAt(moment: number): string | null {
    let low = 0;
    let high = this.versions.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.versions[middle].since <= moment) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    if (low === 0) {
      return null;
    }
    const version = this.versions[low - 1];
    if (version.value === null) {
      return null;
    }
    return version.expiresAt === null || moment < version.expiresAt ? version.value : null;
  }
}

export class InMemoryDatabase {
  private readonly records = new Map<string, Map<string, FieldHistory>>();

  // Level 1
  set(timestamp: number, key: string, field: string, value: string): void {
    this.write(key, field, { since: timestamp, value, expiresAt: null });
  }

  get(timestamp: number, key: string, field: string): string {
    return this.valueAt(key, field, timestamp) ?? "";
  }

  remove(timestamp: number, key: string, field: string): boolean {
    if (this.valueAt(key, field, timestamp) === null) {
      return false;
    }
    this.write(key, field, { since: timestamp, value: null, expiresAt: null });
    return true;
  }

  // Level 2
  scan(timestamp: number, key: string): string[] {
    return this.scanFields(key, "", timestamp);
  }

  scanByPrefix(timestamp: number, key: string, prefix: string): string[] {
    return this.scanFields(key, prefix, timestamp);
  }

  // Level 3
  setWithTtl(timestamp: number, key: string, field: string, value: string, ttl: number): void {
    this.write(key, field, { since: timestamp, value, expiresAt: timestamp + ttl });
  }

  // Level 4
  getAt(timestamp: number, key: string, field: string, atTimestamp: number): string {
    return this.valueAt(key, field, atTimestamp) ?? "";
  }

  scanAt(timestamp: number, key: string, atTimestamp: number): string[] {
    return this.scanFields(key, "", atTimestamp);
  }

  private write(key: string, field: string, version: Version): void {
    let fields = this.records.get(key);
    if (fields === undefined) {
      fields = new Map();
      this.records.set(key, fields);
    }
    let history = fields.get(field);
    if (history === undefined) {
      history = new FieldHistory();
      fields.set(field, history);
    }
    history.record(version);
  }

  private valueAt(key: string, field: string, moment: number): string | null {
    return this.records.get(key)?.get(field)?.valueAt(moment) ?? null;
  }

  private scanFields(key: string, prefix: string, moment: number): string[] {
    const entries: [string, string][] = [];
    for (const [field, history] of this.records.get(key) ?? []) {
      const value = history.valueAt(moment);
      if (field.startsWith(prefix) && value !== null) {
        entries.push([field, value]);
      }
    }
    entries.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return entries.map(([field, value]) => `${field}(${value})`);
  }
}
