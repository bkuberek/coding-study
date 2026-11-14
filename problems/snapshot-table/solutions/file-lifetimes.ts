const NEVER = Number.MAX_SAFE_INTEGER;

interface DataFile {
  path: string;
  partition: string;
  rows: string;
  added: number;
  removed: number;
}

interface Snapshot {
  id: number;
  parent: number;
  timestamp: number;
  operation: string;
  added: DataFile[];
  removed: DataFile[];
}

function liveAt(file: DataFile, snapshot: number): boolean {
  return file.added <= snapshot && snapshot < file.removed;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Snapshots are numbered 1, 2, 3 in commit order, and history is a single line, so a data file is
// live in one interval of snapshots: from the one that added it up to, not including, the one that
// removed it. Each file keeps that interval, each snapshot keeps the files it added and removed,
// and every question is a filter over the files or a walk over the snapshots.
export class SnapshotTable {
  private files = new Map<string, DataFile>();
  private snapshots: Snapshot[] = [];
  private firstRetained = 1;

  // Level 1
  append(files: string[][], timestamp: number): number {
    if (files.length === 0 || !this.fresh(files)) {
      return -1;
    }
    return this.commitChange(files, [], timestamp, null);
  }

  currentSnapshot(): number {
    return this.snapshots.length;
  }

  scan(): string[] {
    return this.scanAt(this.currentSnapshot());
  }

  manifest(snapshotId: number): string[][] {
    if (!this.retained(snapshotId)) {
      return [];
    }
    const entries: string[][] = [];
    for (const file of this.files.values()) {
      let status: string;
      if (liveAt(file, snapshotId)) {
        status = file.added === snapshotId ? "added" : "existing";
      } else if (file.removed === snapshotId) {
        status = "deleted";
      } else {
        continue;
      }
      entries.push([file.path, file.partition, file.rows, status]);
    }
    return entries.sort((a, b) => compareText(a[0], b[0]));
  }

  // Level 2
  deleteFiles(paths: string[], timestamp: number): number {
    if (paths.length === 0 || !this.removable(paths, this.currentSnapshot())) {
      return -1;
    }
    return this.commitChange([], paths, timestamp, null);
  }

  overwrite(partition: string, files: string[][], timestamp: number): number {
    if (files.some((file) => file[1] !== partition) || !this.fresh(files)) {
      return -1;
    }
    const current = this.currentSnapshot();
    const old = [...this.files.values()]
      .filter((file) => file.partition === partition && liveAt(file, current))
      .map((file) => file.path);
    if (old.length === 0 && files.length === 0) {
      return -1;
    }
    return this.commitChange(files, old, timestamp, null);
  }

  scanAt(snapshotId: number): string[] {
    if (!this.retained(snapshotId)) {
      return [];
    }
    return [...this.files.values()]
      .filter((file) => liveAt(file, snapshotId))
      .map((file) => file.path)
      .sort(compareText);
  }

  snapshotAsOf(timestamp: number): number {
    let found = 0;
    for (const snapshot of this.snapshots) {
      if (snapshot.timestamp <= timestamp) {
        found = snapshot.id;
      }
    }
    return found >= this.firstRetained ? found : 0;
  }

  history(): string[][] {
    return this.snapshots
      .slice(this.firstRetained - 1)
      .map((s) => [String(s.id), String(s.parent), String(s.timestamp), s.operation, String(s.added.length), String(s.removed.length)]);
  }

  // Level 3
  commit(base: number, adds: string[][], removes: string[], timestamp: number): string[] {
    const current = this.currentSnapshot();
    const baseOk = (base === 0 && this.firstRetained === 1) || this.retained(base);
    if (!baseOk || (adds.length === 0 && removes.length === 0)) {
      return ["invalid", ""];
    }
    if (!this.fresh(adds) || !this.removable(removes, base)) {
      return ["invalid", ""];
    }
    const removing = new Set(removes);
    const partitions = new Set(removes.map((path) => (this.files.get(path) as DataFile).partition));
    for (const snapshot of this.snapshots.slice(base, current)) {
      const removedTwice = snapshot.removed.some((file) => removing.has(file.path));
      const appended = snapshot.operation !== "replace" && snapshot.added.some((file) => partitions.has(file.partition));
      if (removedTwice || appended) {
        return ["conflict", String(snapshot.id)];
      }
    }
    const outcome = base === current ? "committed" : "rebased";
    return [outcome, String(this.commitChange(adds, removes, timestamp, null))];
  }

  // Level 4
  expireSnapshots(olderThan: number, retainLast: number): string[] {
    const oldFirst = this.firstRetained;
    const lastCandidate = this.currentSnapshot() - retainLast;
    while (this.firstRetained <= lastCandidate && this.snapshots[this.firstRetained - 1].timestamp < olderThan) {
      this.firstRetained++;
    }
    const newFirst = this.firstRetained;
    return [...this.files.values()]
      .filter((file) => oldFirst < file.removed && file.removed <= newFirst)
      .map((file) => file.path)
      .sort(compareText);
  }

  compact(partition: string, maxFileRows: number, timestamp: number): number {
    const current = this.currentSnapshot();
    const small = [...this.files.values()].filter(
      (file) => file.partition === partition && liveAt(file, current) && Number(file.rows) < maxFileRows,
    );
    if (small.length < 2) {
      return -1;
    }
    const rows = small.reduce((total, file) => total + Number(file.rows), 0);
    const path = `${partition}/compacted-${current + 1}`;
    return this.commitChange(
      [[path, partition, String(rows)]],
      small.map((file) => file.path),
      timestamp,
      "replace",
    );
  }

  // Helpers
  private retained(snapshotId: number): boolean {
    return this.firstRetained <= snapshotId && snapshotId <= this.currentSnapshot();
  }

  private fresh(files: string[][]): boolean {
    const paths = files.map((file) => file[0]);
    return new Set(paths).size === paths.length && !paths.some((path) => this.files.has(path));
  }

  private removable(paths: string[], snapshotId: number): boolean {
    if (new Set(paths).size !== paths.length) {
      return false;
    }
    return paths.every((path) => {
      const file = this.files.get(path);
      return file !== undefined && liveAt(file, snapshotId);
    });
  }

  private commitChange(adds: string[][], removes: string[], timestamp: number, operation: string | null): number {
    const parent = this.currentSnapshot();
    const id = parent + 1;
    const kind = operation ?? (adds.length > 0 && removes.length > 0 ? "overwrite" : adds.length > 0 ? "append" : "delete");
    const snapshot: Snapshot = { id, parent, timestamp, operation: kind, added: [], removed: [] };
    for (const path of removes) {
      const file = this.files.get(path) as DataFile;
      file.removed = id;
      snapshot.removed.push(file);
    }
    for (const [path, partition, rows] of adds) {
      const file: DataFile = { path, partition, rows, added: id, removed: NEVER };
      this.files.set(path, file);
      snapshot.added.push(file);
    }
    this.snapshots.push(snapshot);
    return id;
  }
}
