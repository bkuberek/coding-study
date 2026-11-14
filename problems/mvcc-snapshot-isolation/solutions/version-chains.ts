// Every key keeps a chain of committed versions, oldest first, each stamped with the commit time
// of its writer and the id of that writer (0 for a put). A transaction buffers its writes until it
// commits, so the chains only ever hold committed data, and a read is a binary search for the
// newest stamp before the reader's start. Serializable transactions also leave their reads behind,
// even after they commit, and every read-write antidependency between two of them is kept as a
// pair of edges. An edge stops counting as soon as either end aborts.

type State = "active" | "committed" | "aborted";

class Transaction {
  start: number;
  serializable: boolean;
  state: State = "active";
  commitTime = 0;
  writes = new Map<string, string>();
  ins = new Set<number>();
  outs = new Set<number>();

  constructor(start: number, serializable: boolean) {
    this.start = start;
    this.serializable = serializable;
  }
}

class Chain {
  stamps: number[] = [];
  values: string[] = [];
  writers: number[] = [];

  // The number of versions stamped before `time`.
  before(time: number): number {
    let low = 0;
    let high = this.stamps.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.stamps[middle] < time) low = middle + 1;
      else high = middle;
    }
    return low;
  }
}

export class MvccStore {
  private clock = 0;
  private chains = new Map<string, Chain>();
  private transactions = new Map<number, Transaction>();
  private readers = new Map<string, Set<number>>();

  // Level 1
  put(key: string, value: string): number {
    this.clock++;
    this.append(key, value, this.clock, 0);
    return this.clock;
  }

  begin(): number {
    return this.start(false);
  }

  read(tx: number, key: string): string {
    const reader = this.active(tx);
    if (reader === undefined) return "";
    const own = reader.writes.get(key);
    if (own !== undefined) return own;
    if (reader.serializable && !this.recordRead(tx, reader, key)) return "";
    const chain = this.chains.get(key);
    if (chain === undefined) return "";
    const visible = chain.before(reader.start);
    return visible > 0 ? chain.values[visible - 1] : "";
  }

  versions(key: string): string[] {
    const chain = this.chains.get(key);
    if (chain === undefined) return [];
    return chain.stamps.map((stamp, i) => `${stamp}:${chain.values[i]}`).reverse();
  }

  // Level 2
  write(tx: number, key: string, value: string): boolean {
    const writer = this.active(tx);
    if (writer === undefined) return false;
    if (writer.serializable && !this.recordWrite(tx, writer, key)) return false;
    writer.writes.set(key, value);
    return true;
  }

  commit(tx: number): string {
    const t = this.active(tx);
    if (t === undefined) return "not-active";
    for (const key of t.writes.keys()) {
      const chain = this.chains.get(key);
      if (chain !== undefined && chain.stamps[chain.stamps.length - 1] > t.start) {
        t.state = "aborted";
        return "write-conflict";
      }
    }
    if (t.serializable && this.live(t.ins).length > 0 && this.live(t.outs).length > 0) {
      t.state = "aborted";
      return "dangerous-structure";
    }
    this.clock++;
    t.state = "committed";
    t.commitTime = this.clock;
    for (const [key, value] of t.writes) this.append(key, value, this.clock, tx);
    return "committed";
  }

  abort(tx: number): boolean {
    const t = this.active(tx);
    if (t === undefined) return false;
    t.state = "aborted";
    return true;
  }

  status(tx: number): string {
    return this.transactions.get(tx)?.state ?? "unknown";
  }

  // Level 3
  beginSerializable(): number {
    return this.start(true);
  }

  antidependencies(tx: number): string[] {
    const t = this.transactions.get(tx);
    if (t === undefined || t.state === "aborted") return [];
    return [...this.live(t.ins).map((other) => `in:${other}`), ...this.live(t.outs).map((other) => `out:${other}`)];
  }

  // Level 4
  horizon(): number {
    let oldest = this.clock;
    let found = false;
    for (const t of this.transactions.values()) {
      if (t.state === "active" && (!found || t.start < oldest)) {
        oldest = t.start;
        found = true;
      }
    }
    return oldest;
  }

  vacuum(): string[] {
    const limit = this.horizon();
    const removed: string[] = [];
    for (const key of [...this.chains.keys()].sort()) {
      const chain = this.chains.get(key) as Chain;
      const keepFrom = chain.before(limit + 1) - 1;
      if (keepFrom <= 0) continue;
      for (const stamp of chain.stamps.splice(0, keepFrom)) removed.push(`${key}@${stamp}`);
      chain.values.splice(0, keepFrom);
      chain.writers.splice(0, keepFrom);
    }
    return removed;
  }

  // Helpers
  private start(serializable: boolean): number {
    this.clock++;
    this.transactions.set(this.clock, new Transaction(this.clock, serializable));
    return this.clock;
  }

  private active(tx: number): Transaction | undefined {
    const t = this.transactions.get(tx);
    return t !== undefined && t.state === "active" ? t : undefined;
  }

  private append(key: string, value: string, stamp: number, writer: number): void {
    let chain = this.chains.get(key);
    if (chain === undefined) {
      chain = new Chain();
      this.chains.set(key, chain);
    }
    chain.stamps.push(stamp);
    chain.values.push(value);
    chain.writers.push(writer);
  }

  private takesPart(tx: number): boolean {
    const t = this.transactions.get(tx);
    return t !== undefined && t.serializable && t.state !== "aborted";
  }

  // The ids whose transaction has not aborted, sorted as numbers.
  private live(ids: Set<number>): number[] {
    return [...ids].filter((other) => this.transactions.get(other)?.state !== "aborted").sort((a, b) => a - b);
  }

  // The reader misses every version committed after it began and every write still buffered by an
  // active transaction: each such writer gets an edge from the reader.
  private recordRead(tx: number, reader: Transaction, key: string): boolean {
    const chain = this.chains.get(key);
    const committed =
      chain === undefined ? [] : chain.writers.slice(chain.before(reader.start)).filter((writer) => this.takesPart(writer));
    if (committed.some((writer) => this.live((this.transactions.get(writer) as Transaction).outs).length > 0)) {
      reader.state = "aborted";
      return false;
    }
    const buffered: number[] = [];
    for (const [other, t] of this.transactions) {
      if (other !== tx && t.serializable && t.state === "active" && t.writes.has(key)) buffered.push(other);
    }
    let seen = this.readers.get(key);
    if (seen === undefined) {
      seen = new Set();
      this.readers.set(key, seen);
    }
    seen.add(tx);
    for (const writer of [...committed, ...buffered]) this.edge(tx, writer);
    return true;
  }

  // Every reader of the key that overlaps the writer gets an edge to it.
  private recordWrite(tx: number, writer: Transaction, key: string): boolean {
    const overlapping = [...(this.readers.get(key) ?? [])].filter((other) => {
      const t = this.transactions.get(other) as Transaction;
      return other !== tx && this.takesPart(other) && (t.state === "active" || t.commitTime > writer.start);
    });
    const pivotCommitted = overlapping.some((other) => {
      const t = this.transactions.get(other) as Transaction;
      return t.state === "committed" && this.live(t.ins).length > 0;
    });
    if (pivotCommitted) {
      writer.state = "aborted";
      return false;
    }
    for (const reader of overlapping) this.edge(reader, tx);
    return true;
  }

  private edge(reader: number, writer: number): void {
    (this.transactions.get(reader) as Transaction).outs.add(writer);
    (this.transactions.get(writer) as Transaction).ins.add(reader);
  }
}
