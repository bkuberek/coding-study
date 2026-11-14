const ID_PATTERN = /^[a-z0-9_]{1,20}$/;
const NUMBER_PATTERN = /^[0-9]{1,4}$/;
const SCRIPT_PATTERN = /^[SF]*$/;
const MIN_COLUMNS = 5;
const MAX_DURATION = 1000;
const MAX_COST = 1000;
const UNLIMITED = -1;

const PENDING = "pending";
const DONE = "done";
const FAILED = "failed";
const BLOCKED = "blocked";
const SKIPPED = "skipped";
const REPLACED = "replaced";

type Row = string[];

interface Task {
  id: string;
  duration: number;
  cost: number;
  script: string;
  output: string;
  deps: string[];
  row: string[];
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareRows(a: string[], b: string[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i += 1) {
    const order = compareText(a[i], b[i]);
    if (order !== 0) return order;
  }
  return a.length - b.length;
}

function sortedText(items: Iterable<string>): string[] {
  return [...items].sort(compareText);
}

function numberIn(text: string, low: number, high: number): number | null {
  if (!NUMBER_PATTERN.test(text)) return null;
  const value = Number(text);
  return value >= low && value <= high ? value : null;
}

function parseRow(row: string[]): Task | null {
  if (row.length < MIN_COLUMNS || !ID_PATTERN.test(row[0])) return null;
  const duration = numberIn(row[1], 1, MAX_DURATION);
  const cost = numberIn(row[2], 0, MAX_COST);
  if (duration === null || cost === null || !SCRIPT_PATTERN.test(row[3])) return null;
  return {
    id: row[0],
    duration,
    cost,
    script: row[3],
    output: row[4],
    deps: [...new Set(row.slice(5))],
    row: [...row],
  };
}

// One row per group of tasks that wait for each other, found from what each task can reach.
function cycles(tasks: Map<string, Task>): Row[] {
  const reach = new Map<string, Set<string>>();
  for (const [start, task] of tasks) {
    const seen = new Set<string>();
    const stack = task.deps.filter((d) => tasks.has(d));
    while (stack.length > 0) {
      const node = stack.pop() as string;
      if (!seen.has(node)) {
        seen.add(node);
        for (const d of (tasks.get(node) as Task).deps) if (tasks.has(d)) stack.push(d);
      }
    }
    reach.set(start, seen);
  }
  const groups = new Set<string>();
  for (const id of tasks.keys()) {
    const own = reach.get(id) as Set<string>;
    if (own.has(id)) {
      const members = [...own].filter((o) => (reach.get(o) as Set<string>).has(id));
      groups.add(sortedText(members).join(","));
    }
  }
  return [...groups].map((group) => ["cycle", group]);
}

interface Validation {
  errors: Row[];
  tasks: Map<string, Task>;
}

function validate(rows: string[][]): Validation {
  const none = new Map<string, Task>();
  const parsed = rows.map(parseRow);
  const malformed: Row[] = [];
  parsed.forEach((task, i) => {
    if (task === null) malformed.push(["malformed-task", String(i)]);
  });
  if (malformed.length > 0) return { errors: malformed, tasks: none };
  const inOrder = parsed as Task[];
  const counts = new Map<string, number>();
  for (const task of inOrder) counts.set(task.id, (counts.get(task.id) ?? 0) + 1);
  const duplicates = sortedText([...counts].filter(([, n]) => n > 1).map(([id]) => id)).map(
    (id): Row => ["duplicate-id", id],
  );
  if (duplicates.length > 0) return { errors: duplicates, tasks: none };
  const tasks = new Map(inOrder.map((task): [string, Task] => [task.id, task]));
  const unknown: Row[] = [];
  for (const task of inOrder) {
    for (const dep of task.deps) {
      if (!tasks.has(dep)) unknown.push(["unknown-dependency", `${task.id}>${dep}`]);
    }
  }
  const errors = [...cycles(tasks), ...unknown].sort(compareRows);
  return { errors, tasks: errors.length > 0 ? none : tasks };
}

function topological(tasks: Map<string, Task>): string[] {
  const waiting = new Map<string, number>();
  const dependents = new Map<string, string[]>();
  for (const [id, task] of tasks) {
    waiting.set(id, task.deps.length);
    dependents.set(id, []);
  }
  for (const [id, task] of tasks) {
    for (const dep of task.deps) (dependents.get(dep) as string[]).push(id);
  }
  const ready = sortedText([...waiting].filter(([, n]) => n === 0).map(([id]) => id));
  const order: string[] = [];
  while (ready.length > 0) {
    const current = ready.shift() as string;
    order.push(current);
    for (const follower of dependents.get(current) as string[]) {
      const left = (waiting.get(follower) as number) - 1;
      waiting.set(follower, left);
      if (left === 0) {
        ready.push(follower);
        ready.sort(compareText);
      }
    }
  }
  return order;
}

function succeeds(script: string, attempt: number): boolean {
  if (script === "") return true;
  return script[Math.min(attempt, script.length) - 1] === "S";
}

class Execution {
  readonly log: Row[] = [];
  private tasks: Map<string, Task>;
  private readonly status = new Map<string, string>();
  private readonly attempts = new Map<string, number>();
  private readonly span = new Map<string, [number, number]>();
  private readonly seen: Set<string>;
  private readonly tried = new Set<string>();
  private readonly attemptsAllowed: number;
  private readonly replans: Map<string, string[][]>;
  private readonly cap: number;
  private readonly maxCost: number;
  private readonly maxSteps: number;
  private cost = 0;
  private steps = 0;
  private time = 0;
  private wave = 0;
  private stopped = "none";
  private applied = 0;
  private rejected = 0;

  constructor(
    tasks: Map<string, Task>,
    replans: Map<string, string[][]>,
    cap: number,
    maxRetries: number,
    maxCost: number,
    maxSteps: number,
  ) {
    this.replans = replans;
    this.cap = cap;
    this.maxCost = maxCost;
    this.maxSteps = maxSteps;
    this.tasks = new Map(tasks);
    this.attemptsAllowed = 1 + maxRetries;
    for (const id of tasks.keys()) {
      this.status.set(id, PENDING);
      this.attempts.set(id, 0);
    }
    this.seen = new Set(tasks.keys());
  }

  execute(): void {
    while (this.stopped === "none") {
      const ready = sortedText(
        [...this.status]
          .filter(
            ([id, s]) =>
              s === PENDING &&
              (this.tasks.get(id) as Task).deps.every((d) => this.status.get(d) === DONE),
          )
          .map(([id]) => id),
      );
      if (ready.length === 0) break;
      this.wave += 1;
      const batch = ready.slice(0, this.cap);
      this.runWave(batch);
      if (this.stopped === "none") this.replanAfter(batch);
    }
    this.settle();
  }

  private denial(task: Task): string {
    if (this.maxCost !== UNLIMITED && this.cost + task.cost > this.maxCost) return "cost";
    if (this.maxSteps !== UNLIMITED && this.steps + 1 > this.maxSteps) return "steps";
    return "none";
  }

  private runWave(batch: string[]): void {
    const start = this.time;
    let alive = [...batch];
    while (alive.length > 0 && this.stopped === "none") {
      const undecided: string[] = [];
      for (const id of alive) {
        const task = this.tasks.get(id) as Task;
        const reason = this.denial(task);
        if (reason !== "none") {
          this.stopped = reason;
          break;
        }
        this.cost += task.cost;
        this.steps += 1;
        const made = (this.attempts.get(id) as number) + 1;
        this.attempts.set(id, made);
        if (succeeds(task.script, made)) this.status.set(id, DONE);
        else if (made === this.attemptsAllowed) this.status.set(id, FAILED);
        else undecided.push(id);
      }
      alive = undecided;
    }
    const ends: number[] = [];
    for (const id of batch) {
      const made = this.attempts.get(id) as number;
      if (made > 0) {
        if (this.status.get(id) === PENDING) this.status.set(id, FAILED);
        const end = start + made * (this.tasks.get(id) as Task).duration;
        this.span.set(id, [start, end]);
        ends.push(end);
      }
    }
    if (ends.length > 0) this.time = Math.max(...ends);
  }

  private replanAfter(batch: string[]): void {
    for (const id of sortedText(batch)) {
      if (this.status.get(id) === FAILED && this.replans.has(id) && !this.tried.has(id)) {
        this.tried.add(id);
        if (this.tryReplan(id)) return;
      }
    }
  }

  private tryReplan(failed: string): boolean {
    const newRows = this.replans.get(failed) as string[][];
    const keptRows = [...this.tasks]
      .filter(([id]) => this.status.get(id) === DONE)
      .map(([, task]) => [...task.row]);
    const result = validate([...keptRows, ...newRows]);
    const merged = result.tasks;
    let errors = result.errors;
    if (errors.length === 0) {
      errors = sortedText(
        newRows
          .map((row) => row[0])
          .filter((id) => this.seen.has(id) && this.status.get(id) !== DONE),
      ).map((id): Row => ["duplicate-id", id]);
    }
    if (errors.length > 0) {
      this.rejected += 1;
      this.log.push([String(this.wave), failed, "rejected", `${errors[0][0]}:${errors[0][1]}`]);
      return false;
    }
    const removed = [...this.status].filter(([, s]) => s === PENDING).map(([id]) => id);
    for (const id of removed) this.status.set(id, REPLACED);
    const added = [...merged.keys()].filter((id) => !this.seen.has(id));
    for (const id of added) {
      this.tasks.set(id, merged.get(id) as Task);
      this.status.set(id, PENDING);
      this.attempts.set(id, 0);
      this.seen.add(id);
    }
    this.applied += 1;
    this.log.push([
      String(this.wave),
      failed,
      "applied",
      `removed ${removed.length}, added ${added.length}`,
    ]);
    return true;
  }

  // Tasks that never ran are blocked when a task they wait for did not finish, else skipped.
  private settle(): void {
    for (const id of topological(this.tasks)) {
      if (this.status.get(id) === PENDING) {
        const lost = (this.tasks.get(id) as Task).deps.some((d) => {
          const s = this.status.get(d);
          return s === FAILED || s === BLOCKED;
        });
        this.status.set(id, lost ? BLOCKED : SKIPPED);
      }
    }
  }

  rows(): Row[] {
    return sortedText(this.seen).map((id) => {
      const span = this.span.get(id);
      return [
        id,
        this.status.get(id) as string,
        String(this.attempts.get(id)),
        span === undefined ? "" : String(span[0]),
        span === undefined ? "" : String(span[1]),
      ];
    });
  }

  report(): Row[] {
    const ids = (wanted: string): string[] =>
      sortedText([...this.status].filter(([, s]) => s === wanted).map(([id]) => id));
    return [
      ["stopped", this.stopped],
      ["spent", String(this.cost), String(this.steps), String(this.time)],
      ["done", ...ids(DONE)],
      ["failed", ...ids(FAILED)],
      ["blocked", ...ids(BLOCKED)],
      ["skipped", ...ids(SKIPPED)],
      ["replaced", ...ids(REPLACED)],
      ["replans", String(this.applied), String(this.rejected)],
      ["results", ...ids(DONE).map((id) => `${id}=${(this.tasks.get(id) as Task).output}`)],
    ];
  }
}

export class PlanRunner {
  private tasks = new Map<string, Task>();
  private readonly replans = new Map<string, string[][]>();
  private maxCost = UNLIMITED;
  private maxSteps = UNLIMITED;
  private last: Execution | null = null;

  setPlan(tasks: string[][]): string[][] {
    const { errors, tasks: parsed } = validate(tasks);
    if (errors.length === 0) this.tasks = parsed;
    return errors;
  }

  order(): string[] {
    return topological(this.tasks);
  }

  private waves(cap: number): [string, number, number][][] {
    const done = new Set<string>();
    const waves: [string, number, number][][] = [];
    let time = 0;
    while (done.size < this.tasks.size) {
      const ready = sortedText(
        [...this.tasks]
          .filter(([id, task]) => !done.has(id) && task.deps.every((d) => done.has(d)))
          .map(([id]) => id),
      ).slice(0, cap);
      const wave = ready.map((id): [string, number, number] => [
        id,
        time,
        time + (this.tasks.get(id) as Task).duration,
      ]);
      waves.push(wave);
      for (const id of ready) done.add(id);
      time = Math.max(...wave.map(([, , end]) => end));
    }
    return waves;
  }

  timeline(cap: number): string[][] {
    return this.waves(cap).flatMap((wave, index) =>
      wave.map(([id, start, end]) => [String(index + 1), id, String(start), String(end)]),
    );
  }

  makespan(cap: number): number {
    const waves = this.waves(cap);
    return waves.length === 0 ? 0 : Math.max(...waves[waves.length - 1].map(([, , end]) => end));
  }

  criticalPath(): string[] {
    const best = new Map<string, [number, string[]]>();
    const better = (a: [number, string[]], b: [number, string[]]): boolean =>
      a[0] !== b[0] ? a[0] > b[0] : compareRows(a[1], b[1]) < 0;
    for (const id of topological(this.tasks)) {
      const task = this.tasks.get(id) as Task;
      let pick: [number, string[]] = [0, []];
      let first = true;
      for (const dep of task.deps) {
        const candidate = best.get(dep) as [number, string[]];
        if (first || better(candidate, pick)) pick = candidate;
        first = false;
      }
      best.set(id, [pick[0] + task.duration, [...pick[1], id]]);
    }
    let winner: [number, string[]] | null = null;
    for (const candidate of best.values()) {
      if (winner === null || better(candidate, winner)) winner = candidate;
    }
    return winner === null ? [] : winner[1];
  }

  setReplan(failedId: string, tasks: string[][]): boolean {
    const isNew = !this.replans.has(failedId);
    this.replans.set(
      failedId,
      tasks.map((row) => [...row]),
    );
    return isNew;
  }

  run(cap: number, maxRetries: number): string[][] {
    const execution = new Execution(
      this.tasks,
      this.replans,
      cap,
      maxRetries,
      this.maxCost,
      this.maxSteps,
    );
    execution.execute();
    this.last = execution;
    return execution.rows();
  }

  replanLog(): string[][] {
    return this.last === null ? [] : this.last.log.map((row) => [...row]);
  }

  setBudget(maxCost: number, maxSteps: number): void {
    this.maxCost = maxCost;
    this.maxSteps = maxSteps;
  }

  report(): string[][] {
    return this.last === null ? [] : this.last.report();
  }
}
