// Tasks describe the state a host should be in. Running a task compares that state with the
// host's and changes the host only when they differ, so a second run finds nothing to do. A run
// works through the hosts in batches; in each batch it applies every task to every host still
// standing, then the handlers that a change notified. A check run does the same on copies of the
// hosts, so later tasks see what earlier ones would have done while the real hosts stay as they
// were.
const COUNTED = ["ok", "changed", "failed", "skipped"] as const;
const WHOLE = /^-?[0-9]+$/;

interface Host {
  files: Map<string, string>;
  packages: Map<string, string>;
  facts: Map<string, string>;
}

type Action = [kind: string, target: string, value: string];
type Counts = Map<string, Map<string, number>>;

function copyHost(host: Host): Host {
  return { files: new Map(host.files), packages: new Map(host.packages), facts: host.facts };
}

function zeros(): Map<string, number> {
  return new Map(COUNTED.map((name) => [name, 0] as [string, number]));
}

// The truth of one condition, or null when it cannot be decided.
function compare(fact: string, operator: string, value: string): boolean | null {
  if (operator === "==") {
    return fact === value;
  }
  if (operator === "!=") {
    return fact !== value;
  }
  if (!WHOLE.test(fact) || !WHOLE.test(value)) {
    return null;
  }
  const left = Number(fact);
  const right = Number(value);
  switch (operator) {
    case "<":
      return left < right;
    case "<=":
      return left <= right;
    case ">":
      return left > right;
    default:
      return left >= right;
  }
}

function apply(host: Host, kind: string, target: string, value: string): void {
  if (kind === "file") {
    host.files.set(target, value);
  } else if (kind === "package" && value === "present") {
    if (!host.packages.has(target)) {
      host.packages.set(target, "stopped");
    }
  } else if (kind === "package") {
    host.packages.delete(target);
  } else {
    host.packages.set(target, value === "restarted" ? "running" : value);
  }
}

// The state a task of this kind compares with, or null for a missing service.
function current(host: Host, kind: string, target: string): string | null {
  if (kind === "file") {
    return host.files.get(target) ?? "";
  }
  if (kind === "package") {
    return host.packages.has(target) ? "present" : "absent";
  }
  return host.packages.get(target) ?? null;
}

function change(host: Host, [kind, target, value]: Action): [string, string[]] {
  const before = current(host, kind, target);
  if (before === null) {
    return ["failed", []];
  }
  if (before === value && value !== "restarted") {
    return ["ok", []];
  }
  apply(host, kind, target, value);
  return ["changed", [before, value]];
}

export class Converger {
  private hosts = new Map<string, Host>();
  private tasks = new Map<string, Action>();
  private handlers = new Map<string, Action>();
  private links = new Map<string, string[]>();
  private conditions = new Map<string, Action[]>();
  private batch = 0;
  private counts: Counts = new Map();

  // Level 1
  addHost(host: string): boolean {
    if (this.hosts.has(host)) {
      return false;
    }
    this.hosts.set(host, { files: new Map(), packages: new Map(), facts: new Map() });
    return true;
  }

  setState(host: string, kind: string, target: string, value: string): boolean {
    const found = this.hosts.get(host);
    if (found === undefined) {
      return false;
    }
    apply(found, kind, target, value);
    return true;
  }

  addTask(name: string, kind: string, target: string, value: string): boolean {
    if (this.tasks.has(name)) {
      return false;
    }
    this.tasks.set(name, [kind, target, value]);
    return true;
  }

  run(): string[][] {
    const counts: Counts = new Map([...this.hosts.keys()].map((host) => [host, zeros()]));
    const rows = this.play(this.hosts, false, counts);
    this.counts = counts;
    return rows;
  }

  state(host: string): string[][] {
    const found = this.hosts.get(host);
    if (found === undefined) {
      return [];
    }
    const rows: string[][] = [];
    for (const [path, content] of found.files) {
      rows.push(["file", path, content]);
    }
    for (const [name, service] of found.packages) {
      rows.push(["package", name, "present"], ["service", name, service]);
    }
    const key = (row: string[]): string => `${row[0]}\u0000${row[1]}`;
    return rows.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
  }

  // Level 2
  check(): string[][] {
    const copies = new Map([...this.hosts].map(([name, host]) => [name, copyHost(host)]));
    const counts: Counts = new Map([...this.hosts.keys()].map((host) => [host, zeros()]));
    return this.play(copies, true, counts);
  }

  // Level 3
  addHandler(name: string, kind: string, target: string, value: string): boolean {
    if (this.handlers.has(name)) {
      return false;
    }
    this.handlers.set(name, [kind, target, value]);
    return true;
  }

  notifies(task: string, handler: string): boolean {
    if (!this.tasks.has(task) || !this.handlers.has(handler)) {
      return false;
    }
    const linked = this.links.get(task) ?? [];
    this.links.set(task, linked);
    if (linked.includes(handler)) {
      return false;
    }
    linked.push(handler);
    return true;
  }

  // Level 4
  setFact(host: string, key: string, value: string): boolean {
    const found = this.hosts.get(host);
    if (found === undefined) {
      return false;
    }
    const isNew = !found.facts.has(key);
    found.facts.set(key, value);
    return isNew;
  }

  onlyIf(task: string, fact: string, comparison: string, value: string): boolean {
    if (!this.tasks.has(task)) {
      return false;
    }
    const list = this.conditions.get(task) ?? [];
    list.push([fact, comparison, value]);
    this.conditions.set(task, list);
    return true;
  }

  setBatchSize(size: number): boolean {
    const changed = size !== this.batch;
    this.batch = size;
    return changed;
  }

  summary(): string[][] {
    return [...this.hosts.keys()].map((host) => {
      const counts = this.counts.get(host) ?? zeros();
      return [host, ...COUNTED.map((name) => String(counts.get(name)))];
    });
  }

  // Running
  private play(hosts: Map<string, Host>, dry: boolean, counts: Counts): string[][] {
    const names = [...hosts.keys()];
    const size = this.batch > 0 ? this.batch : Math.max(names.length, 1);
    const rows: string[][] = [];
    const record = (host: string, name: string, status: string, diff: string[]): void => {
      const tally = counts.get(host)!;
      tally.set(status, tally.get(status)! + 1);
      rows.push(dry ? [host, name, status, ...diff] : [host, name, status]);
    };
    for (let start = 0; start < names.length; start += size) {
      const batch = names.slice(start, start + size);
      const failed = new Set<string>();
      const notified = new Map(batch.map((host) => [host, new Set<string>()]));
      for (const [task, action] of this.tasks) {
        for (const host of batch) {
          if (failed.has(host)) {
            continue;
          }
          const [status, diff] = this.task(hosts.get(host)!, task, action);
          if (status === "failed") {
            failed.add(host);
          } else if (status === "changed") {
            for (const handler of this.links.get(task) ?? []) {
              notified.get(host)!.add(handler);
            }
          }
          record(host, task, status, diff);
        }
      }
      for (const [handler, action] of this.handlers) {
        for (const host of batch) {
          if (failed.has(host) || !notified.get(host)!.has(handler)) {
            continue;
          }
          const [status, diff] = change(hosts.get(host)!, action);
          if (status === "failed") {
            failed.add(host);
          }
          record(host, handler, status, diff);
        }
      }
      if (failed.size === batch.length) {
        break;
      }
    }
    return rows;
  }

  private task(host: Host, task: string, action: Action): [string, string[]] {
    for (const [fact, operator, wanted] of this.conditions.get(task) ?? []) {
      const have = host.facts.get(fact);
      if (have === undefined) {
        return ["failed", []];
      }
      const holds = compare(have, operator, wanted);
      if (holds === null) {
        return ["failed", []];
      }
      if (!holds) {
        return ["skipped", []];
      }
    }
    return change(host, action);
  }
}
