// A permanent value of a key from a given sequence number on; null marks a removal.
interface PermanentValue {
  readonly sequence: number;
  readonly value: string | null;
}

export class TransactionalStore {
  private readonly data = new Map<string, string>(); // the current view, open transactions included
  private readonly counts = new Map<string, number>();
  // One undo log per open transaction, innermost last: key -> value before its first change.
  private readonly undo: Map<string, string | null>[] = [];
  private readonly history = new Map<string, PermanentValue[]>();
  private sequence = 0;
  private readonly snapshots: number[] = [];

  // Level 1
  set(timestamp: number, key: string, value: string): void {
    this.change(key, value);
  }

  get(timestamp: number, key: string): string {
    return this.data.get(key) ?? "";
  }

  remove(timestamp: number, key: string): boolean {
    if (!this.data.has(key)) {
      return false;
    }
    this.change(key, null);
    return true;
  }

  count(timestamp: number, value: string): number {
    return this.counts.get(value) ?? 0;
  }

  // Level 2
  begin(timestamp: number): void {
    this.undo.push(new Map());
  }

  rollback(timestamp: number): boolean {
    const changed = this.undo.pop();
    if (changed === undefined) {
      return false;
    }
    for (const [key, previous] of changed) {
      this.assign(key, previous);
    }
    return true;
  }

  // Level 3
  depth(timestamp: number): number {
    return this.undo.length;
  }

  // Level 4
  commit(timestamp: number): number {
    const changed = this.undo.pop();
    if (changed === undefined) {
      return -1;
    }
    const enclosing = this.undo.at(-1);
    if (enclosing !== undefined) {
      for (const [key, previous] of changed) {
        if (!enclosing.has(key)) {
          enclosing.set(key, previous);
        }
      }
      return 0;
    }
    this.makePermanent(changed.keys());
    this.snapshots.push(this.sequence);
    return this.snapshots.length;
  }

  getSnapshot(timestamp: number, version: number, key: string): string {
    if (version < 1 || version > this.snapshots.length) {
      return "";
    }
    const sequence = this.snapshots[version - 1];
    const values = this.history.get(key) ?? [];
    let low = 0;
    let high = values.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (values[middle].sequence <= sequence) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return (low === 0 ? null : values[low - 1].value) ?? "";
  }

  private change(key: string, value: string | null): void {
    const innermost = this.undo.at(-1);
    if (innermost === undefined) {
      this.assign(key, value);
      this.makePermanent([key]);
      return;
    }
    if (!innermost.has(key)) {
      innermost.set(key, this.data.get(key) ?? null);
    }
    this.assign(key, value);
  }

  private assign(key: string, value: string | null): void {
    const previous = this.data.get(key);
    if (previous !== undefined) {
      this.counts.set(previous, (this.counts.get(previous) ?? 0) - 1);
    }
    if (value === null) {
      this.data.delete(key);
    } else {
      this.data.set(key, value);
      this.counts.set(value, (this.counts.get(value) ?? 0) + 1);
    }
  }

  private makePermanent(keys: Iterable<string>): void {
    this.sequence++;
    for (const key of keys) {
      const values = this.history.get(key) ?? [];
      values.push({ sequence: this.sequence, value: this.data.get(key) ?? null });
      this.history.set(key, values);
    }
  }
}
