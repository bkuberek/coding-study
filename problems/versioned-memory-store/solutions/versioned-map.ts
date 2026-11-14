const ACCEPTED = 1;
const REFUSED = 0;
const NO_VALUE = "";

interface Entry {
  version: number;
  value: string;
}

const NEVER_CHANGED: Entry = { version: 0, value: NO_VALUE };

export class MemoryStore {
  // A forgotten key keeps its entry, with no value, so its version never goes back.
  private readonly entries = new Map<string, Entry>();

  get(key: string): string {
    return (this.entries.get(key) ?? NEVER_CHANGED).value;
  }

  version(key: string): number {
    return (this.entries.get(key) ?? NEVER_CHANGED).version;
  }

  write(key: string, expectedVersion: number, value: string): number[] {
    return this.change(key, expectedVersion, value);
  }

  forget(key: string, expectedVersion: number): number[] {
    return this.change(key, expectedVersion, NO_VALUE);
  }

  private change(key: string, expectedVersion: number, value: string): number[] {
    const current = this.version(key);
    if (expectedVersion !== current) {
      return [REFUSED, current];
    }
    this.entries.set(key, { version: current + 1, value });
    return [ACCEPTED, current + 1];
  }
}
