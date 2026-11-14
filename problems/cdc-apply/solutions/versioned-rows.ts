const OK = "ok";
const SKIPPED = "skipped";
const NEVER = -1;

type Change = [op: string, row: string[]];

function byCodes(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// A map from key to row holds the table. A second map holds each key's version, the position at
// which its last change became visible, and keeps it when the row is deleted: that tombstone is
// what stops an old insert from bringing a deleted row back.
//
// A change is skipped when its position is not after the key's version, or not after the
// snapshot the table started from. A transaction's changes wait in a buffer until its commit,
// then run into an overlay, a small map of the rows they change, which is written into the table
// only when every change worked.
export class ReplicaTable {
  private names: string[];
  private table = new Map<string, string[]>();
  private versions = new Map<string, number>();
  private floor = 0;
  private schemaVersion = 0;
  private readonly staged = new Map<string, Change[]>();

  constructor(columns: string[]) {
    this.names = [...columns];
  }

  // Level 1
  apply(op: string, row: string[]): string {
    const code = this.check(this.table.has(row[0]), op, row);
    if (code === OK) {
      if (op === "delete") {
        this.table.delete(row[0]);
      } else {
        this.table.set(row[0], [...row]);
      }
    }
    return code;
  }

  rows(): string[][] {
    return [...this.table.keys()].sort(byCodes).map((key) => [...this.table.get(key)!]);
  }

  // Level 2
  applyAt(lsn: number, op: string, row: string[]): string {
    const key = row[0];
    if (lsn <= this.floor || lsn <= this.version(key)) {
      return SKIPPED;
    }
    const code = this.apply(op, row);
    if (code === OK) {
      this.versions.set(key, lsn);
    }
    return code;
  }

  version(key: string): number {
    return this.versions.get(key) ?? NEVER;
  }

  // Level 3
  loadSnapshot(lsn: number, snapshot: string[][]): void {
    this.table = new Map(snapshot.map((row) => [row[0], [...row]]));
    this.versions = new Map(snapshot.map((row) => [row[0], lsn]));
    this.floor = lsn;
  }

  stage(tx: string, op: string, row: string[]): void {
    const changes = this.staged.get(tx) ?? [];
    changes.push([op, [...row]]);
    this.staged.set(tx, changes);
  }

  commit(lsn: number, tx: string): string {
    const changes = this.staged.get(tx) ?? [];
    this.staged.delete(tx);
    if (lsn <= this.floor) {
      return SKIPPED;
    }
    const overlay = new Map<string, string[] | null>();
    for (const [op, row] of changes) {
      const key = row[0];
      if (lsn <= this.version(key)) {
        continue;
      }
      const present = overlay.has(key) ? overlay.get(key) !== null : this.table.has(key);
      const code = this.check(present, op, row);
      if (code !== OK) {
        return code;
      }
      overlay.set(key, op === "delete" ? null : row);
    }
    if (overlay.size === 0) {
      return SKIPPED;
    }
    for (const [key, row] of overlay) {
      if (row === null) {
        this.table.delete(key);
      } else {
        this.table.set(key, row);
      }
      this.versions.set(key, lsn);
    }
    return OK;
  }

  rollback(tx: string): void {
    this.staged.delete(tx);
  }

  // Level 4
  alterAt(lsn: number, change: string[]): string {
    if (lsn <= this.floor || lsn <= this.schemaVersion) {
      return SKIPPED;
    }
    const code = this.alter(change);
    if (code === OK) {
      this.schemaVersion = lsn;
    }
    return code;
  }

  columns(): string[] {
    return [...this.names];
  }

  compare(sourceColumns: string[], sourceRows: string[][]): string[][] {
    const mine = new Set(this.names);
    const theirs = new Set(sourceColumns);
    const report: string[][] = [];
    for (const name of [...new Set([...mine, ...theirs])].sort(byCodes)) {
      if (!mine.has(name)) {
        report.push(["missing-column", name]);
      } else if (!theirs.has(name)) {
        report.push(["extra-column", name]);
      }
    }
    const common = this.names.filter((name) => theirs.has(name)).sort(byCodes);
    const source = new Map(sourceRows.map((row) => [row[0], row]));
    const keys = [...new Set([...source.keys(), ...this.table.keys()])].sort(byCodes);
    for (const key of keys) {
      const here = this.table.get(key);
      const there = source.get(key);
      if (here === undefined) {
        report.push(["missing-row", key]);
      } else if (there === undefined) {
        report.push(["extra-row", key]);
      } else {
        for (const name of common) {
          const a = here[this.names.indexOf(name)];
          const b = there[sourceColumns.indexOf(name)];
          if (a !== b) {
            report.push(["value-differs", key, name, a, b]);
          }
        }
      }
    }
    return report;
  }

  // Changes
  private check(present: boolean, op: string, row: string[]): string {
    if (op !== "delete" && row.length !== this.names.length) {
      return "column-count";
    }
    if (op === "insert") {
      return present ? "duplicate-key" : OK;
    }
    return present ? OK : "unknown-key";
  }

  private alter(change: string[]): string {
    const [kind, name] = change;
    if (kind === "add") {
      if (this.names.includes(name)) {
        return "duplicate-column";
      }
      this.names.push(name);
      for (const row of this.table.values()) {
        row.push(change[2]);
      }
      return OK;
    }
    const index = this.names.indexOf(name);
    if (index < 0) {
      return "unknown-column";
    }
    if (kind === "drop") {
      if (index === 0) {
        return "key-column";
      }
      this.names.splice(index, 1);
      for (const row of this.table.values()) {
        row.splice(index, 1);
      }
      return OK;
    }
    if (this.names.includes(change[2])) {
      return "duplicate-column";
    }
    this.names[index] = change[2];
    return OK;
  }
}
