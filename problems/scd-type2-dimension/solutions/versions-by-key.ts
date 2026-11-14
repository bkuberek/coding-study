const OPEN_END = 99991231;
const UNKNOWN_MEMBER = 0;

interface Version {
  key: number;
  businessKey: string;
  values: string[];
  validFrom: number;
  validTo: number;
}

function rowOfVersion(version: Version): string[] {
  return [
    String(version.key),
    version.businessKey,
    ...version.values,
    String(version.validFrom),
    String(version.validTo),
    version.validTo === OPEN_END ? "Y" : "N",
  ];
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Every business key keeps its versions in an array sorted by validFrom, and the versions never
// overlap, so the version valid at a date is one binary search away. Untracked attributes hold
// one value per business key, copied into every version, and the date of the latest load that
// carried the key decides whether a row may still overwrite them.
export class DimensionTable {
  private position = new Map<string, number>();
  private tracked: number[] = [];
  private bySurrogate = new Map<number, Version>();
  private versions = new Map<string, Version[]>();
  private lastLoad = new Map<string, number>();
  private nextKey = 1;

  constructor(attributes: string[]) {
    attributes.forEach((name, index) => this.position.set(name, index));
  }

  // Level 1
  load(rows: string[][], loadDate: number): number[] {
    return this.apply(rows, loadDate).counts;
  }

  lookup(businessKey: string): number {
    const versions = this.versions.get(businessKey);
    if (versions === undefined || versions[versions.length - 1].validTo !== OPEN_END) {
      return -1;
    }
    return versions[versions.length - 1].key;
  }

  rowOf(surrogateKey: number): string[] {
    const version = this.bySurrogate.get(surrogateKey);
    return version === undefined ? [] : rowOfVersion(version);
  }

  size(): number {
    return this.bySurrogate.size;
  }

  // Level 2
  trackHistory(attribute: string): boolean {
    const index = this.position.get(attribute);
    if (index === undefined || this.tracked.includes(index)) {
      return false;
    }
    this.tracked.push(index);
    return true;
  }

  history(businessKey: string): string[][] {
    return (this.versions.get(businessKey) ?? []).map(rowOfVersion);
  }

  // Level 3
  lookupAt(businessKey: string, asOf: number): number {
    return this.validAt(businessKey, asOf)?.key ?? -1;
  }

  snapshotAt(asOf: number): string[][] {
    const rows: string[][] = [];
    for (const businessKey of this.sortedKeys()) {
      const version = this.validAt(businessKey, asOf);
      if (version !== undefined) {
        rows.push(rowOfVersion(version));
      }
    }
    return rows;
  }

  resolveFacts(facts: string[][]): string[][] {
    return facts.map(([factId, businessKey, eventDate]) => {
      if (!this.versions.has(businessKey)) {
        return [factId, String(UNKNOWN_MEMBER), "unknown-key"];
      }
      const version = this.validAt(businessKey, Number(eventDate));
      if (version === undefined) {
        return [factId, String(UNKNOWN_MEMBER), "no-version"];
      }
      return [factId, String(version.key), version.validTo === OPEN_END ? "current" : "late"];
    });
  }

  // Level 4
  loadFull(rows: string[][], loadDate: number): number[] {
    const { counts, present } = this.apply(rows, loadDate);
    let closed = 0;
    for (const businessKey of this.sortedKeys()) {
      const versions = this.versions.get(businessKey) as Version[];
      const last = versions[versions.length - 1];
      if (!present.has(businessKey) && last.validTo === OPEN_END) {
        last.validTo = loadDate;
        closed++;
      }
    }
    return [...counts, closed];
  }

  fullHistory(): string[][] {
    return this.sortedKeys().flatMap((businessKey) => (this.versions.get(businessKey) as Version[]).map(rowOfVersion));
  }

  // Helpers
  private apply(rows: string[][], loadDate: number): { counts: number[]; present: Set<string> } {
    const latest = new Map<string, string[]>();
    for (const row of rows) {
      latest.set(row[0], row.slice(1));
    }
    const counts = [0, 0, 0];
    for (const businessKey of [...latest.keys()].sort(compareText)) {
      const values = latest.get(businessKey) as string[];
      if (!this.versions.has(businessKey)) {
        this.versions.set(businessKey, []);
        this.lastLoad.set(businessKey, loadDate);
        this.insert(businessKey, [...values], loadDate, OPEN_END);
        counts[0]++;
      } else if (this.merge(businessKey, values, loadDate)) {
        counts[1]++;
      } else {
        counts[2]++;
      }
    }
    return { counts, present: new Set(latest.keys()) };
  }

  private merge(businessKey: string, values: string[], loadDate: number): boolean {
    const versions = this.versions.get(businessKey) as Version[];
    let changed = false;
    if (loadDate >= (this.lastLoad.get(businessKey) as number)) {
      this.lastLoad.set(businessKey, loadDate);
      for (const index of this.untracked()) {
        if (versions[0].values[index] !== values[index]) {
          for (const version of versions) {
            version.values[index] = values[index];
          }
          changed = true;
        }
      }
    }
    const holder = this.validAt(businessKey, loadDate);
    if (holder !== undefined) {
      if (this.tracked.every((index) => holder.values[index] === values[index])) {
        return changed;
      }
      if (holder.validFrom === loadDate) {
        for (const index of this.tracked) {
          holder.values[index] = values[index];
        }
        return true;
      }
      const end = holder.validTo;
      holder.validTo = loadDate;
      this.insert(businessKey, this.combine(versions[0], values), loadDate, end);
      return true;
    }
    const next = versions.find((version) => version.validFrom > loadDate);
    this.insert(businessKey, this.combine(versions[0], values), loadDate, next === undefined ? OPEN_END : next.validFrom);
    return true;
  }

  // The incoming tracked values with the key's untracked values.
  private combine(shared: Version, values: string[]): string[] {
    const combined = [...shared.values];
    for (const index of this.tracked) {
      combined[index] = values[index];
    }
    return combined;
  }

  private untracked(): number[] {
    return [...this.position.values()].filter((index) => !this.tracked.includes(index));
  }

  private insert(businessKey: string, values: string[], validFrom: number, validTo: number): void {
    const version: Version = { key: this.nextKey++, businessKey, values, validFrom, validTo };
    this.bySurrogate.set(version.key, version);
    const versions = this.versions.get(businessKey) as Version[];
    versions.splice(this.startsAtOrBefore(versions, validFrom), 0, version);
  }

  // The number of versions whose validFrom is at or before the date.
  private startsAtOrBefore(versions: Version[], date: number): number {
    let low = 0;
    let high = versions.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (versions[middle].validFrom <= date) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  }

  private validAt(businessKey: string, asOf: number): Version | undefined {
    const versions = this.versions.get(businessKey);
    if (versions === undefined) {
      return undefined;
    }
    const at = this.startsAtOrBefore(versions, asOf) - 1;
    if (at < 0 || asOf >= versions[at].validTo) {
      return undefined;
    }
    return versions[at];
  }

  private sortedKeys(): string[] {
    return [...this.versions.keys()].sort(compareText);
  }
}
