// Each process keeps the current value of its three clocks: a Lamport counter, a vector and a
// hybrid pair. Every event updates them by the rules of its kind and keeps a copy as its stamp,
// so every question afterwards is answered from the stamps alone.
interface Stamp {
  process: number;
  lamport: number;
  vector: number[];
  l: number;
  c: number;
  wall: number;
  isSend: boolean;
  key: string;
  value: string;
}

function atMost(first: number[], second: number[]): boolean {
  return first.every((entry, index) => entry <= second[index]);
}

export class LogicalClocks {
  private processes: number;
  private lamportNow: number[];
  private vectorNow: number[][];
  private hybridNow: Array<[number, number]>;
  private events = new Map<string, Stamp>();
  private received = new Set<string>();
  private writes = new Map<string, string[]>();

  constructor(processes: number) {
    this.processes = processes;
    this.lamportNow = new Array<number>(processes).fill(0);
    this.vectorNow = Array.from({ length: processes }, () => new Array<number>(processes).fill(0));
    this.hybridNow = Array.from({ length: processes }, (): [number, number] => [0, 0]);
  }

  // Level 1
  local(process: number, event: string, wall: number): number {
    return this.record(process, event, wall, null, false);
  }

  send(process: number, event: string, wall: number): number {
    return this.record(process, event, wall, null, true);
  }

  receive(process: number, event: string, message: string, wall: number): number {
    const sent = this.events.get(message);
    if (sent === undefined || !sent.isSend || this.received.has(message)) return -1;
    if (sent.process === process) return -1;
    const stamp = this.record(process, event, wall, sent, false);
    if (stamp !== -1) this.received.add(message);
    return stamp;
  }

  totalOrder(): string[] {
    return this.sortedBy((one, other) => one.lamport - other.lamport || one.process - other.process);
  }

  // Level 2
  vector(event: string): number[] {
    const stamp = this.events.get(event);
    return stamp === undefined ? [] : stamp.vector.slice();
  }

  compare(first: string, second: string): string {
    const one = this.events.get(first);
    const other = this.events.get(second);
    if (one === undefined || other === undefined) return "";
    if (first === second) return "same";
    if (atMost(one.vector, other.vector)) return "before";
    if (atMost(other.vector, one.vector)) return "after";
    return "concurrent";
  }

  // Level 3
  write(process: number, event: string, key: string, value: string, wall: number): number {
    const stamp = this.record(process, event, wall, null, false);
    if (stamp !== -1) {
      const written = this.events.get(event)!;
      written.key = key;
      written.value = value;
      if (!this.writes.has(key)) this.writes.set(key, []);
      this.writes.get(key)!.push(event);
    }
    return stamp;
  }

  read(process: number, key: string): string[] {
    if (process < 0 || process >= this.processes) return [];
    const now = this.vectorNow[process];
    const known = (this.writes.get(key) ?? [])
      .map((name) => this.events.get(name)!)
      .filter((stamp) => atMost(stamp.vector, now));
    const siblings = known.filter(
      (stamp) => !known.some((other) => other !== stamp && atMost(stamp.vector, other.vector)),
    );
    return siblings.map((stamp) => stamp.value).sort();
  }

  concurrentWrites(key: string): string[][] {
    const names = (this.writes.get(key) ?? []).slice().sort();
    const pairs: string[][] = [];
    names.forEach((first, index) => {
      for (const second of names.slice(index + 1)) {
        if (this.compare(first, second) === "concurrent") pairs.push([first, second]);
      }
    });
    return pairs;
  }

  // Level 4
  hlc(event: string): number[] {
    const stamp = this.events.get(event);
    return stamp === undefined ? [] : [stamp.l, stamp.c];
  }

  hlcOrder(): string[] {
    return this.sortedBy(
      (one, other) => one.l - other.l || one.c - other.c || one.process - other.process,
    );
  }

  maxOffset(): number {
    let largest = 0;
    for (const stamp of this.events.values()) largest = Math.max(largest, stamp.l - stamp.wall);
    return largest;
  }

  // Shared
  private sortedBy(order: (one: Stamp, other: Stamp) => number): string[] {
    return [...this.events.keys()].sort((a, b) => order(this.events.get(a)!, this.events.get(b)!));
  }

  private record(
    process: number,
    event: string,
    wall: number,
    sent: Stamp | null,
    isSend: boolean,
  ): number {
    if (process < 0 || process >= this.processes || this.events.has(event)) return -1;
    let lamport = this.lamportNow[process];
    let vector = this.vectorNow[process].slice();
    if (sent === null) {
      lamport += 1;
    } else {
      lamport = Math.max(lamport, sent.lamport) + 1;
      vector = vector.map((mine, index) => Math.max(mine, sent.vector[index]));
    }
    vector[process] += 1;
    const [l, c] = nextHybrid(this.hybridNow[process], wall, sent);
    this.lamportNow[process] = lamport;
    this.vectorNow[process] = vector;
    this.hybridNow[process] = [l, c];
    this.events.set(event, { process, lamport, vector, l, c, wall, isSend, key: "", value: "" });
    return lamport;
  }
}

// The update of Kulkarni et al.: `l` is the largest physical reading heard of, and `c` counts the
// events since `l` last changed.
function nextHybrid(current: [number, number], wall: number, sent: Stamp | null): [number, number] {
  const [oldL, oldC] = current;
  if (sent === null) {
    const l = Math.max(oldL, wall);
    return [l, l === oldL ? oldC + 1 : 0];
  }
  const l = Math.max(oldL, sent.l, wall);
  if (l === oldL && l === sent.l) return [l, Math.max(oldC, sent.c) + 1];
  if (l === oldL) return [l, oldC + 1];
  if (l === sent.l) return [l, sent.c + 1];
  return [l, 0];
}
