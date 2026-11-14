const DONE = "done";
const FAILED = "failed";
const MISSING = "missing";

type Partition = [task: string, day: number];
type Outcome = [round: number, status: string, attempts: number];

function byCodes(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function id(task: string, day: number | string): string {
  return `${task}\u0000${day}`;
}

// Keeps a sorted array sorted, which stands in for a min-heap of names.
function insertSorted(names: string[], name: string): void {
  let low = 0;
  let high = names.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (names[mid] < name) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  names.splice(low, 0, name);
}

// Tasks and their dependencies form a graph. The order counts the unlisted dependencies of each
// task and keeps the ready names sorted, so that the smallest ready name goes next.
//
// A ledger keyed by (task, day) records each partition's state. Every write gets a number, and the
// partition remembers the number of each input it read, which is all it takes to tell a stale
// partition and to find what a backfill must rerun. Runs and backfills share one attempt loop,
// which follows the scripted outcomes and the task's retries.
export class PipelineScheduler {
  private readonly deps = new Map<string, string[]>();
  private readonly windows = new Map<string, number>();
  private readonly retries = new Map<string, number>();
  private readonly scripts = new Map<string, string[]>();
  private readonly state = new Map<string, string>();
  private readonly written = new Map<string, number>();
  private readonly reads = new Map<string, Map<string, number>>();
  private writes = 0;

  // Level 1
  addTask(name: string, deps: string[]): boolean {
    if (this.deps.has(name)) {
      return false;
    }
    this.deps.set(name, [...new Set(deps)]);
    return true;
  }

  validate(): string[][] {
    const problems: string[][] = [];
    for (const [task, deps] of this.deps) {
      for (const dep of deps) {
        if (!this.deps.has(dep)) {
          problems.push(["unknown-dependency", task, dep]);
        }
      }
    }
    const listed = new Set(this.order());
    for (const task of this.deps.keys()) {
      if (!listed.has(task) && this.reachesItself(task)) {
        problems.push(["cycle", task]);
      }
    }
    return problems.sort((a, b) => {
      for (let i = 0; i < Math.min(a.length, b.length); i++) {
        const c = byCodes(a[i], b[i]);
        if (c !== 0) {
          return c;
        }
      }
      return a.length - b.length;
    });
  }

  runOrder(): string[] {
    return this.validate().length > 0 ? [] : this.order();
  }

  // Level 2
  setWindow(task: string, dep: string, days: number): boolean {
    if (!(this.deps.get(task) ?? []).includes(dep)) {
      return false;
    }
    this.windows.set(id(task, dep), days);
    return true;
  }

  markDone(task: string, day: number): void {
    this.store(task, day);
  }

  runnable(day: number): string[] {
    return [...this.deps.keys()]
      .filter((task) => this.state.get(id(task, day)) !== DONE && this.inputsDone(task, day))
      .sort(byCodes);
  }

  // Level 3
  setRetries(task: string, retries: number): void {
    this.retries.set(task, retries);
  }

  script(task: string, day: number, outcomes: string[]): void {
    this.scripts.set(id(task, day), [...outcomes]);
  }

  run(day: number): string[][] {
    return this.runOrder().map((task) => {
      if (!this.inputsDone(task, day)) {
        return [task, "skipped", "0"];
      }
      const [attempts, succeeded] = this.attempt(task, day);
      return [task, succeeded ? "success" : "failed", String(attempts)];
    });
  }

  status(task: string, day: number): string {
    return this.state.get(id(task, day)) ?? MISSING;
  }

  // Level 4
  stale(day: number): string[] {
    return [...this.deps.keys()].filter((task) => this.isStale(task, day)).sort(byCodes);
  }

  plan(task: string, fromDay: number, toDay: number): string[][] {
    return this.makePlan(task, fromDay, toDay).map(([name, day]) => [String(day), name]);
  }

  backfill(task: string, fromDay: number, toDay: number, cap: number): string[][] {
    const plan = this.makePlan(task, fromDay, toDay);
    const planned = new Set(plan.map(([name, day]) => id(name, day)));
    const outcome = new Map<string, Outcome>();
    let round = 0;
    while (outcome.size < plan.length) {
      round += 1;
      // Inputs come before their users in plan order, so one pass settles every skip.
      for (const [name, day] of plan) {
        if (!outcome.has(id(name, day)) && this.blocked(name, day, planned, outcome)) {
          outcome.set(id(name, day), [round, "skipped", 0]);
        }
      }
      const ready = plan
        .filter(([name, day]) => !outcome.has(id(name, day)))
        .filter(([name, day]) =>
          this.inputs(name, day)
            .filter(([n, d]) => planned.has(id(n, d)))
            .every(([n, d]) => outcome.get(id(n, d))?.[1] === "success"),
        )
        .slice(0, cap);
      for (const [name, day] of ready) {
        const [attempts, succeeded] = this.attempt(name, day);
        outcome.set(id(name, day), [round, succeeded ? "success" : "failed", attempts]);
      }
    }
    const rank = new Map(this.runOrder().map((name, i) => [name, i]));
    return plan
      .map(([name, day]) => ({ name, day, result: outcome.get(id(name, day))! }))
      .sort((a, b) => a.result[0] - b.result[0] || a.day - b.day || rank.get(a.name)! - rank.get(b.name)!)
      .map(({ name, day, result }) => [String(result[0]), String(day), name, result[1], String(result[2])]);
  }

  // The graph
  private users(): Map<string, string[]> {
    const users = new Map<string, string[]>([...this.deps.keys()].map((task) => [task, []]));
    for (const [task, deps] of this.deps) {
      for (const dep of deps) {
        users.get(dep)?.push(task);
      }
    }
    return users;
  }

  private order(): string[] {
    const waiting = new Map<string, number>();
    for (const [task, deps] of this.deps) {
      waiting.set(task, deps.filter((dep) => this.deps.has(dep)).length);
    }
    const users = this.users();
    const ready = [...waiting.keys()].filter((task) => waiting.get(task) === 0).sort(byCodes);
    const order: string[] = [];
    while (ready.length > 0) {
      const task = ready.shift()!;
      order.push(task);
      for (const user of users.get(task)!) {
        const left = waiting.get(user)! - 1;
        waiting.set(user, left);
        if (left === 0) {
          insertSorted(ready, user);
        }
      }
    }
    return order;
  }

  private reachesItself(start: string): boolean {
    const seen = new Set<string>();
    const stack = this.deps.get(start)!.filter((dep) => this.deps.has(dep));
    while (stack.length > 0) {
      const task = stack.pop()!;
      if (task === start) {
        return true;
      }
      if (!seen.has(task)) {
        seen.add(task);
        stack.push(...this.deps.get(task)!.filter((dep) => this.deps.has(dep)));
      }
    }
    return false;
  }

  // The partitions
  private inputs(task: string, day: number): Partition[] {
    const inputs: Partition[] = [];
    for (const dep of this.deps.get(task)!) {
      const width = this.windows.get(id(task, dep)) ?? 1;
      for (let d = Math.max(0, day - width + 1); d <= day; d++) {
        inputs.push([dep, d]);
      }
    }
    return inputs;
  }

  private current(task: string, day: number): number {
    return this.state.get(id(task, day)) === DONE ? this.written.get(id(task, day))! : 0;
  }

  private inputsDone(task: string, day: number): boolean {
    return this.inputs(task, day).every(([n, d]) => this.state.get(id(n, d)) === DONE);
  }

  private store(task: string, day: number): void {
    this.writes += 1;
    this.state.set(id(task, day), DONE);
    this.written.set(id(task, day), this.writes);
    this.reads.set(id(task, day), new Map(this.inputs(task, day).map(([n, d]) => [id(n, d), this.current(n, d)])));
  }

  private attempt(task: string, day: number): [number, boolean] {
    const script = this.scripts.get(id(task, day)) ?? [];
    const limit = 1 + (this.retries.get(task) ?? 0);
    for (let attempt = 1; attempt <= limit; attempt++) {
      if ((script.shift() ?? "ok") === "ok") {
        this.store(task, day);
        return [attempt, true];
      }
    }
    this.state.set(id(task, day), FAILED);
    return [limit, false];
  }

  private isStale(task: string, day: number): boolean {
    if (this.state.get(id(task, day)) !== DONE) {
      return false;
    }
    for (const [n, d] of this.inputs(task, day)) {
      if (this.current(n, d) !== this.reads.get(id(task, day))!.get(id(n, d))) {
        return true;
      }
    }
    return false;
  }

  private makePlan(task: string, fromDay: number, toDay: number): Partition[] {
    const users = this.users();
    const planned = new Map<string, Partition>();
    for (let day = fromDay; day <= toDay; day++) {
      planned.set(id(task, day), [task, day]);
    }
    const frontier = [...planned.values()];
    while (frontier.length > 0) {
      const [upstream, day] = frontier.pop()!;
      for (const user of users.get(upstream)!) {
        const width = this.windows.get(id(user, upstream)) ?? 1;
        for (let later = day; later < day + width; later++) {
          if (this.state.get(id(user, later)) === DONE && !planned.has(id(user, later))) {
            planned.set(id(user, later), [user, later]);
            frontier.push([user, later]);
          }
        }
      }
    }
    const rank = new Map(this.runOrder().map((name, i) => [name, i]));
    return [...planned.values()].sort((a, b) => a[1] - b[1] || rank.get(a[0])! - rank.get(b[0])!);
  }

  private blocked(task: string, day: number, planned: Set<string>, outcome: Map<string, Outcome>): boolean {
    for (const [n, d] of this.inputs(task, day)) {
      if (planned.has(id(n, d))) {
        const result = outcome.get(id(n, d));
        if (result !== undefined && result[1] !== "success") {
          return true;
        }
      } else if (this.state.get(id(n, d)) !== DONE) {
        return true;
      }
    }
    return false;
  }
}
