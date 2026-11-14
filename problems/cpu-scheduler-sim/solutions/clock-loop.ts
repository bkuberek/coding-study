// A workload of processes and the result of the latest run over it.
//
// First come, first served and shortest job first run each process to completion, so they jump
// from one completion to the next. Round robin, the feedback queue and the cores advance a clock
// one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
// the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
// then a steal. One core records its segments, merging a slice that continues the one before.
// Round robin is the case of one core without stealing.

interface Segment {
  pid: string;
  start: number;
  end: number;
}

class Core {
  segments: Segment[] = [];
  last: string | null = null;
  switches = 0;
  busy = 0;

  run(pid: string, start: number, end: number): void {
    const tail = this.segments[this.segments.length - 1];
    if (tail !== undefined && tail.pid === pid && tail.end === start) {
      tail.end = end;
    } else {
      if (this.last !== null && this.last !== pid) this.switches += 1;
      this.segments.push({ pid, start, end });
    }
    this.last = pid;
    this.busy += end - start;
  }
}

class Run {
  readonly pids: string[];
  readonly first = new Map<string, number>();
  readonly done = new Map<string, number>();
  readonly cores: Core[];
  migrations = 0;
  makespan = 0;

  constructor(pids: string[], cores: number) {
    this.pids = [...pids];
    this.cores = Array.from({ length: cores }, () => new Core());
  }

  started(pid: string, time: number): void {
    if (!this.first.has(pid)) this.first.set(pid, time);
  }

  timelines(): string[][] {
    return this.cores.map((core) => core.segments.map((s) => `${s.pid}:${s.start}-${s.end}`));
  }
}

function gcd(a: number, b: number): number {
  while (b !== 0) [a, b] = [b, a % b];
  return a;
}

function fraction(numerator: number, denominator: number): string {
  const common = gcd(numerator, denominator);
  return `${numerator / common}/${denominator / common}`;
}

export class CpuScheduler {
  private pids: string[] = [];
  private arrival = new Map<string, number>();
  private burst = new Map<string, number>();
  private latest: Run | null = null;

  // Level 1
  addProcess(pid: string, arrival: number, burst: number): boolean {
    if (this.arrival.has(pid)) return false;
    this.pids.push(pid);
    this.arrival.set(pid, arrival);
    this.burst.set(pid, burst);
    return true;
  }

  runFcfs(): string[] {
    const run = new Run(this.pids, 1);
    let clock = 0;
    for (const pid of this.byArrival()) {
      clock = this.runToCompletion(run, pid, Math.max(clock, this.arrival.get(pid)!));
    }
    return this.keep(run, clock)[0];
  }

  runSjf(): string[] {
    const run = new Run(this.pids, 1);
    const position = new Map(this.pids.map((pid, index) => [pid, index]));
    const key = (pid: string): number[] => [this.burst.get(pid)!, this.arrival.get(pid)!, position.get(pid)!];
    const pending = [...this.pids];
    let clock = 0;
    while (pending.length > 0) {
      const ready = pending.filter((pid) => this.arrival.get(pid)! <= clock);
      if (ready.length === 0) {
        clock = Math.min(...pending.map((pid) => this.arrival.get(pid)!));
        continue;
      }
      const pid = ready.reduce((best, p) => (lessThan(key(p), key(best)) ? p : best));
      pending.splice(pending.indexOf(pid), 1);
      clock = this.runToCompletion(run, pid, clock);
    }
    return this.keep(run, clock)[0];
  }

  waitingTime(pid: string): number {
    const turnaround = this.turnaroundTime(pid);
    return turnaround === -1 ? -1 : turnaround - this.burst.get(pid)!;
  }

  turnaroundTime(pid: string): number {
    const done = this.latest?.done.get(pid);
    return done === undefined ? -1 : done - this.arrival.get(pid)!;
  }

  averageWaiting(): string {
    return this.average((pid) => this.waitingTime(pid));
  }

  averageTurnaround(): string {
    return this.average((pid) => this.turnaroundTime(pid));
  }

  // Level 2
  runRoundRobin(quantum: number): string[] {
    return this.roundRobin(1, quantum, false)[0];
  }

  responseTime(pid: string): number {
    const first = this.latest?.first.get(pid);
    return first === undefined ? -1 : first - this.arrival.get(pid)!;
  }

  averageResponse(): string {
    return this.average((pid) => this.responseTime(pid));
  }

  contextSwitches(): number {
    if (this.latest === null) return -1;
    return this.latest.cores.reduce((sum, core) => sum + core.switches, 0);
  }

  // Level 3
  runMlfq(quanta: number[], boostPeriod: number): string[] {
    const run = new Run(this.pids, 1);
    const core = run.cores[0];
    const remaining = new Map(this.burst);
    const arrivals = this.byArrival();
    let next = 0;
    let queues: string[][] = quanta.map(() => []);
    const level = new Map<string, number>();
    const used = new Map<string, number>();
    let running: string | null = null;
    let left = this.pids.length;
    let clock = 0;
    for (;;) {
      let demoted: string | null = null;
      if (running !== null) {
        if (remaining.get(running) === 0) {
          run.done.set(running, clock);
          running = null;
          left -= 1;
        } else if (used.get(running) === quanta[level.get(running)!]) {
          level.set(running, Math.min(level.get(running)! + 1, quanta.length - 1));
          used.set(running, 0);
          demoted = running;
          running = null;
        }
      }
      if (left === 0) break;
      while (next < arrivals.length && this.arrival.get(arrivals[next]) === clock) {
        const pid = arrivals[next++];
        level.set(pid, 0);
        used.set(pid, 0);
        queues[0].push(pid);
      }
      if (demoted !== null) queues[level.get(demoted)!].push(demoted);
      if (boostPeriod > 0 && clock > 0 && clock % boostPeriod === 0) {
        const merged = queues.flat();
        queues = quanta.map((_, i) => (i === 0 ? merged : []));
        for (const pid of running === null ? merged : [...merged, running]) {
          level.set(pid, 0);
          used.set(pid, 0);
        }
      }
      if (running !== null && queues.slice(0, level.get(running)!).some((q) => q.length > 0)) {
        queues[level.get(running)!].push(running);
        running = null;
      }
      if (running === null) {
        const queue = queues.find((q) => q.length > 0);
        running = queue === undefined ? null : queue.shift()!;
      }
      if (running !== null) {
        run.started(running, clock);
        core.run(running, clock, clock + 1);
        remaining.set(running, remaining.get(running)! - 1);
        used.set(running, used.get(running)! + 1);
      }
      clock += 1;
    }
    return this.keep(run, clock)[0];
  }

  // Level 4
  runMulticore(cores: number, quantum: number, steal: boolean): string[][] {
    return this.roundRobin(cores, quantum, steal);
  }

  utilization(core: number): string {
    if (this.latest === null || core < 0 || core >= this.latest.cores.length) return "";
    return fraction(this.latest.cores[core].busy, this.latest.makespan);
  }

  migrations(): number {
    return this.latest === null ? -1 : this.latest.migrations;
  }

  // The clock loops
  private roundRobin(cores: number, quantum: number, steal: boolean): string[][] {
    const run = new Run(this.pids, cores);
    const remaining = new Map(this.burst);
    const arrivals = this.byArrival();
    let next = 0;
    const queues: string[][] = Array.from({ length: cores }, () => []);
    const running: (string | null)[] = new Array(cores).fill(null);
    const used: number[] = new Array(cores).fill(0);
    let left = this.pids.length;
    let clock = 0;
    for (;;) {
      const expired: (string | null)[] = new Array(cores).fill(null);
      for (let c = 0; c < cores; c++) {
        const pid = running[c];
        if (pid !== null && remaining.get(pid) === 0) {
          run.done.set(pid, clock);
          running[c] = null;
          left -= 1;
        } else if (pid !== null && used[c] === quantum) {
          expired[c] = pid;
          running[c] = null;
        }
      }
      if (left === 0) break;
      while (next < arrivals.length && this.arrival.get(arrivals[next]) === clock) {
        let target = 0;
        let lowest = Infinity;
        for (let c = 0; c < cores; c++) {
          const load = queues[c].length + (running[c] !== null ? 1 : 0) + (expired[c] !== null ? 1 : 0);
          if (load < lowest) {
            lowest = load;
            target = c;
          }
        }
        queues[target].push(arrivals[next++]);
      }
      for (let c = 0; c < cores; c++) {
        const back = expired[c];
        if (back !== null) queues[c].push(back);
        if (running[c] === null && queues[c].length > 0) {
          running[c] = queues[c].shift()!;
          used[c] = 0;
        }
      }
      for (let c = 0; steal && c < cores; c++) {
        if (running[c] !== null) continue;
        let victim = 0;
        for (let v = 1; v < cores; v++) {
          if (queues[v].length > queues[victim].length) victim = v;
        }
        if (queues[victim].length > 0) {
          running[c] = queues[victim].pop()!;
          used[c] = 0;
          run.migrations += 1;
        }
      }
      for (let c = 0; c < cores; c++) {
        const pid = running[c];
        if (pid === null) continue;
        run.started(pid, clock);
        run.cores[c].run(pid, clock, clock + 1);
        remaining.set(pid, remaining.get(pid)! - 1);
        used[c] += 1;
      }
      clock += 1;
    }
    return this.keep(run, clock);
  }

  private runToCompletion(run: Run, pid: string, start: number): number {
    const end = start + this.burst.get(pid)!;
    run.started(pid, start);
    run.cores[0].run(pid, start, end);
    run.done.set(pid, end);
    return end;
  }

  private byArrival(): string[] {
    return [...this.pids].sort((a, b) => this.arrival.get(a)! - this.arrival.get(b)!);
  }

  private keep(run: Run, makespan: number): string[][] {
    run.makespan = makespan;
    this.latest = run;
    return run.timelines();
  }

  private average(metric: (pid: string) => number): string {
    if (this.latest === null) return "";
    const total = this.latest.pids.reduce((sum, pid) => sum + metric(pid), 0);
    return fraction(total, this.latest.pids.length);
  }
}

function lessThan(a: number[], b: number[]): boolean {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i] < b[i];
  }
  return false;
}
