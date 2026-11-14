type Totals = { start: number; key: number; count: number; sum: number };

function byStartThenKey(a: { start: number; key: number }, b: { start: number; key: number }): number {
  return a.start - b.start || a.key - b.key;
}

function bump(groups: Map<string, Totals>, start: number, key: number, value: number): void {
  const id = `${start},${key}`;
  let totals = groups.get(id);
  if (totals === undefined) {
    totals = { start, key, count: 0, sum: 0 };
    groups.set(id, totals);
  }
  totals.count += 1;
  totals.sum += value;
}

// Every event is kept in a log, so the batch views of levels 1 and 2 can group the whole stream
// in any way they are asked.
//
// The stream of levels 3 and 4 keeps a map from (start, key) to a running count and sum for the
// windows not yet emitted, and a second map for the windows already emitted that can still be
// corrected. After each event the watermark moves, the open windows it has passed are emitted in
// order, and the corrected windows it has left behind are forgotten.
export class StreamWindows {
  private readonly events: [number, number, number][] = [];
  private size = 0;
  private lateness = 0;
  private grace = 0;
  private mark = 0;
  private readonly open = new Map<string, Totals>();
  private readonly closed = new Map<string, Totals>();
  private out: number[][] = [];
  private readonly side: number[][] = [];
  private emitted = 0;
  private updated = 0;

  // Level 1
  add(key: number, time: number, value: number): void {
    this.events.push([key, time, value]);
    if (this.size > 0) {
      this.stream(key, time, value);
    }
  }

  tumbling(size: number): number[][] {
    const groups = new Map<string, Totals>();
    for (const [key, time, value] of this.events) {
      bump(groups, time - (time % size), key, value);
    }
    return this.rows(groups, size);
  }

  // Level 2
  hopping(size: number, slide: number): number[][] {
    const groups = new Map<string, Totals>();
    for (const [key, time, value] of this.events) {
      for (let start = time - (time % slide); start > time - size; start -= slide) {
        bump(groups, start, key, value);
      }
    }
    return this.rows(groups, size);
  }

  sessions(gap: number): number[][] {
    const byKey = new Map<number, [number, number][]>();
    for (const [key, time, value] of this.events) {
      const list = byKey.get(key) ?? [];
      list.push([time, value]);
      byKey.set(key, list);
    }
    const rows: number[][] = [];
    for (const [key, list] of byKey) {
      list.sort((a, b) => a[0] - b[0]);
      let row: number[] | null = null;
      for (const [time, value] of list) {
        if (row !== null && time < row[2]) {
          row[2] = time + gap;
          row[3] += 1;
          row[4] += value;
        } else {
          row = [key, time, time + gap, 1, value];
          rows.push(row);
        }
      }
    }
    return rows.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  }

  // Level 3
  configure(size: number, lateness: number): void {
    this.size = size;
    this.lateness = lateness;
  }

  watermark(): number {
    return this.mark;
  }

  pending(): number[][] {
    return this.rows(this.open, this.size);
  }

  poll(): number[][] {
    const out = this.out;
    this.out = [];
    return out;
  }

  // Level 4
  allowUpdates(grace: number): void {
    this.grace = grace;
  }

  dropped(): number[][] {
    return this.side.map((event) => [...event]);
  }

  stats(): number[] {
    return [this.emitted, this.updated, this.side.length];
  }

  // The stream
  private rows(groups: Map<string, Totals>, size: number): number[][] {
    return [...groups.values()].sort(byStartThenKey).map((t) => this.row(t, size, t.count, t.sum));
  }

  private row(t: Totals, size: number, count: number, sum: number): number[] {
    return [t.key, t.start, t.start + size, count, sum];
  }

  private stream(key: number, time: number, value: number): void {
    const start = time - (time % this.size);
    const end = start + this.size;
    if (end > this.mark) {
      bump(this.open, start, key, value);
    } else if (this.mark < end + this.grace) {
      this.correct(start, key, value);
    } else {
      this.side.push([key, time, value]);
    }
    this.advance(time - this.lateness);
  }

  private correct(start: number, key: number, value: number): void {
    const id = `${start},${key}`;
    const old = this.closed.get(id);
    if (old === undefined) {
      const first = { start, key, count: 1, sum: value };
      this.closed.set(id, first);
      this.emitted += 1;
      this.out.push(this.row(first, this.size, first.count, first.sum));
    } else {
      this.out.push(this.row(old, this.size, -old.count, -old.sum));
      old.count += 1;
      old.sum += value;
      this.updated += 1;
      this.out.push(this.row(old, this.size, old.count, old.sum));
    }
  }

  private advance(candidate: number): void {
    if (candidate <= this.mark) {
      return;
    }
    this.mark = candidate;
    const due = [...this.open.entries()]
      .filter(([, t]) => t.start + this.size <= this.mark)
      .sort((a, b) => byStartThenKey(a[1], b[1]));
    for (const [id, totals] of due) {
      this.open.delete(id);
      this.out.push(this.row(totals, this.size, totals.count, totals.sum));
      this.closed.set(id, totals);
      this.emitted += 1;
    }
    for (const [id, totals] of [...this.closed.entries()]) {
      if (totals.start + this.size + this.grace <= this.mark) {
        this.closed.delete(id);
      }
    }
  }
}
