// Desired and actual resources are maps of attributes. A plan resolves the references of the
// desired resources in dependency order, which tells for each resource whether it is created,
// updated, replaced, left alone or deleted, then turns those actions into steps joined by
// before-rules and lists the steps in the smallest order by (rank, address) that keeps every rule.
// Apply walks the same steps, skips those behind a failure, and records the state after each step
// that succeeds.
const UNKNOWN = "<unknown>";
const FORCES = "forces-replacement";
const CREATE_FIRST = "create-before-destroy";
const DELETE_FIRST = "destroy-before-create";

type Attributes = Map<string, string>;

interface Step {
  verb: string;
  address: string;
  tag: string;
  rank: number;
  mode: string;
  diff: string[][];
  before: Step[];
  after: Step[];
}

function newStep(verb: string, address: string, tag: string, rank: number): Step {
  return { verb, address, tag, rank, mode: "", diff: [], before: [], after: [] };
}

function reference(value: string): [string, string] | null {
  if (!value.startsWith("${") || !value.endsWith("}")) {
    return null;
  }
  const [kind, name, key] = value.slice(2, -1).split(".");
  return [`${kind}.${name}`, key];
}

function kindOf(address: string): string {
  return address.slice(0, address.indexOf("."));
}

function compare(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function sortedKeys<V>(map: Map<string, V>): string[] {
  return [...map.keys()].sort(compare);
}

function byKey(rows: string[][]): string[][] {
  return rows.sort((a, b) => compare(a[1], b[1]));
}

function removed(attributes: Attributes): string[][] {
  return sortedKeys(attributes).map((key) => ["-", key, attributes.get(key)!]);
}

function toMap(attributes: string[][]): Attributes {
  return new Map(attributes.map(([key, value]) => [key, value] as [string, string]));
}

export class PlanEngine {
  private desired = new Map<string, Attributes>();
  private current = new Map<string, Attributes>();
  private deps = new Map<string, Set<string>>();
  private old = new Map<string, Attributes>();
  private oldDeps = new Map<string, Set<string>>();
  private forces = new Set<string>();
  private computedKeys = new Map<string, Set<string>>();
  private marked = new Set<string>();

  // Level 1
  desire(address: string, attributes: string[][]): boolean {
    const isNew = !this.desired.has(address);
    this.desired.set(address, toMap(attributes));
    return isNew;
  }

  remove(address: string): boolean {
    return this.desired.delete(address);
  }

  observe(address: string, attributes: string[][]): boolean {
    const isNew = !this.current.has(address);
    this.current.set(address, toMap(attributes));
    return isNew;
  }

  plan(): string[][] {
    const [errors, steps] = this.build();
    if (errors.length > 0) {
      return errors;
    }
    const rows: string[][] = [];
    for (const step of steps) {
      rows.push(step.tag ? [step.verb, step.address, step.tag] : [step.verb, step.address]);
      rows.push(...step.diff);
    }
    return rows;
  }

  // Level 2
  observeDependency(address: string, dependsOn: string): boolean {
    if (!this.current.has(address) || !this.current.has(dependsOn)) {
      return false;
    }
    const links = this.deps.get(address) ?? new Set<string>();
    this.deps.set(address, links);
    if (links.has(dependsOn)) {
      return false;
    }
    links.add(dependsOn);
    return true;
  }

  // Level 3
  forceReplacement(resourceType: string, key: string): boolean {
    const id = `${resourceType}.${key}`;
    if (this.forces.has(id)) {
      return false;
    }
    this.forces.add(id);
    return true;
  }

  computed(resourceType: string, key: string): boolean {
    const names = this.computedKeys.get(resourceType) ?? new Set<string>();
    this.computedKeys.set(resourceType, names);
    if (names.has(key)) {
      return false;
    }
    names.add(key);
    return true;
  }

  createBeforeDestroy(address: string): boolean {
    if (this.marked.has(address)) {
      return false;
    }
    this.marked.add(address);
    return true;
  }

  // Level 4
  apply(failures: string[][], values: string[][]): string[][] {
    const [errors, steps] = this.build();
    if (errors.length > 0) {
      return errors;
    }
    const failing = new Set(failures.map(([verb, address]) => `${verb} ${address}`));
    const assigned = new Map(values.map(([a, k, v]) => [`${a} ${k}`, v] as [string, string]));
    const status = new Map<Step, string>();
    const rows: string[][] = [];
    for (const step of steps) {
      let outcome = "ok";
      if (step.before.some((prior) => status.get(prior) !== "ok")) {
        outcome = "skipped";
      } else if (step.verb !== "no-op" && failing.has(`${step.verb} ${step.address}`)) {
        outcome = "failed";
      } else {
        this.perform(step, assigned);
      }
      status.set(step, outcome);
      rows.push([step.verb, step.address, outcome]);
    }
    return rows;
  }

  state(): string[][] {
    const addresses = [...new Set([...this.current.keys(), ...this.old.keys()])].sort(compare);
    const rows: string[][] = [];
    for (const address of addresses) {
      for (const [role, objects] of [
        ["current", this.current],
        ["old", this.old],
      ] as const) {
        const attributes = objects.get(address);
        if (attributes !== undefined) {
          const flat = sortedKeys(attributes).flatMap((key) => [key, attributes.get(key)!]);
          rows.push([address, role, ...flat]);
        }
      }
    }
    return rows;
  }

  // Planning
  private isComputed(address: string, key: string): boolean {
    return this.computedKeys.get(kindOf(address))?.has(key) ?? false;
  }

  private computedOf(address: string): string[] {
    return [...(this.computedKeys.get(kindOf(address)) ?? [])].sort(compare);
  }

  private links(): [string[][], Map<string, Set<string>>] {
    const errors: string[][] = [];
    const needs = new Map<string, Set<string>>();
    for (const address of this.desired.keys()) {
      needs.set(address, new Set());
    }
    for (const address of sortedKeys(this.desired)) {
      const attributes = this.desired.get(address)!;
      for (const key of sortedKeys(attributes)) {
        const target = reference(attributes.get(key)!);
        if (target === null) {
          continue;
        }
        const [other, wanted] = target;
        const declared = this.desired.get(other);
        if (declared !== undefined && (declared.has(wanted) || this.isComputed(other, wanted))) {
          needs.get(address)!.add(other);
        } else {
          errors.push(["error", "unknown-reference", address, key, `${other}.${wanted}`]);
        }
      }
    }
    return [errors, needs];
  }

  private static cycles(needs: Map<string, Set<string>>): string[][] {
    const reach = new Map<string, Set<string>>();
    for (const [start, targets] of needs) {
      const seen = new Set<string>();
      const stack = [...targets];
      while (stack.length > 0) {
        const node = stack.pop()!;
        if (!seen.has(node)) {
          seen.add(node);
          stack.push(...needs.get(node)!);
        }
      }
      reach.set(start, seen);
    }
    const groups = new Map<string, string[]>();
    for (const node of needs.keys()) {
      if (reach.get(node)!.has(node)) {
        const group = [...reach.get(node)!].filter((other) => reach.get(other)!.has(node));
        group.sort(compare);
        groups.set(group.join(" "), group);
      }
    }
    return [...groups.values()]
      .sort((a, b) => compare(a[0], b[0]))
      .map((group) => ["error", "cycle", ...group]);
  }

  private static dependencyOrder(needs: Map<string, Set<string>>): string[] {
    const waiting = new Map<string, number>();
    const users = new Map<string, string[]>();
    for (const [address, targets] of needs) {
      waiting.set(address, targets.size);
      users.set(address, []);
    }
    for (const [address, targets] of needs) {
      for (const target of targets) {
        users.get(target)!.push(address);
      }
    }
    const ready = [...needs.keys()].filter((address) => waiting.get(address) === 0);
    const order: string[] = [];
    while (ready.length > 0) {
      ready.sort(compare);
      const address = ready.shift()!;
      order.push(address);
      for (const user of users.get(address)!) {
        waiting.set(user, waiting.get(user)! - 1);
        if (waiting.get(user) === 0) {
          ready.push(user);
        }
      }
    }
    return order;
  }

  private createFirst(needs: Map<string, Set<string>>): Set<string> {
    const found = new Set<string>();
    const stack = [...this.marked].filter((address) => this.desired.has(address));
    while (stack.length > 0) {
      const address = stack.pop()!;
      if (!found.has(address)) {
        found.add(address);
        stack.push(...needs.get(address)!);
      }
    }
    return found;
  }

  private build(): [string[][], Step[]] {
    const [errors, needs] = this.links();
    errors.push(...PlanEngine.cycles(needs));
    if (errors.length > 0) {
      return [errors, []];
    }
    const early = this.createFirst(needs);
    const action = new Map<string, string>();
    const resolved = new Map<string, Attributes>();
    const applies = new Map<string, Step>();
    const deletes = new Map<string, Step>();

    for (const address of PlanEngine.dependencyOrder(needs)) {
      const values: Attributes = new Map();
      for (const [key, value] of this.desired.get(address)!) {
        const target = reference(value);
        if (target === null) {
          values.set(key, value);
        } else if (this.isComputed(target[0], target[1])) {
          const replaced = ["create", "replace"].includes(action.get(target[0])!);
          values.set(key, replaced ? UNKNOWN : this.current.get(target[0])!.get(target[1])!);
        } else {
          values.set(key, resolved.get(target[0])!.get(target[1])!);
        }
      }
      resolved.set(address, values);
      const [kind, step] = this.classify(address, values);
      action.set(address, kind);
      applies.set(address, step);
      if (kind === "replace") {
        const half = newStep("delete", address, "replace", 1);
        half.mode = early.has(address) ? CREATE_FIRST : DELETE_FIRST;
        deletes.set(address, half);
      }
    }
    for (const [address, attributes] of this.current) {
      if (!this.desired.has(address)) {
        const step = newStep("delete", address, "", 1);
        step.diff = removed(attributes);
        deletes.set(address, step);
      }
    }
    for (const [address, attributes] of this.old) {
      const step = newStep("delete", address, "old", 1);
      step.diff = removed(attributes);
      deletes.set(address, step);
    }

    const link = (first: Step, second: Step): void => {
      first.after.push(second);
      second.before.push(first);
    };
    for (const [address, targets] of needs) {
      for (const target of targets) {
        link(applies.get(target)!, applies.get(address)!);
      }
    }
    for (const [address, step] of deletes) {
      const held = step.tag === "old" ? this.oldDeps : this.deps;
      for (const target of held.get(address) ?? []) {
        const gone = deletes.get(target);
        if (gone !== undefined) {
          link(step, gone);
        }
      }
    }
    for (const [address, step] of applies) {
      if (!this.current.has(address)) {
        continue;
      }
      for (const target of this.deps.get(address) ?? []) {
        const gone = deletes.get(target);
        if (gone !== undefined && gone.mode !== DELETE_FIRST) {
          link(step, gone);
        }
      }
    }
    for (const [address, step] of deletes) {
      if (step.mode === DELETE_FIRST) {
        link(step, applies.get(address)!);
      } else if (step.mode === CREATE_FIRST) {
        link(applies.get(address)!, step);
      }
    }
    return [[], PlanEngine.order([...applies.values(), ...deletes.values()])];
  }

  private classify(address: string, values: Attributes): [string, Step] {
    const computed = this.computedOf(address);
    const existing = this.current.get(address);
    if (existing === undefined) {
      const step = newStep("create", address, "", 0);
      const rows = [...values].map(([key, value]) => ["+", key, value]);
      rows.push(...computed.map((name) => ["+", name, UNKNOWN]));
      step.diff = byKey(rows);
      return ["create", step];
    }
    const actual: Attributes = new Map(
      [...existing].filter(([key]) => !this.isComputed(address, key)),
    );
    const keys = [...new Set([...values.keys(), ...actual.keys()])].sort(compare);
    const rows: string[][] = [];
    let forced = false;
    for (const key of keys) {
      const before = actual.get(key);
      const after = values.get(key);
      if (before === after) {
        continue;
      }
      const row =
        before === undefined
          ? ["+", key, after!]
          : after === undefined
            ? ["-", key, before]
            : ["~", key, before, after];
      if (this.forces.has(`${kindOf(address)}.${key}`)) {
        row.push(FORCES);
        forced = true;
      }
      rows.push(row);
    }
    if (rows.length === 0) {
      return ["no-op", newStep("no-op", address, "", 0)];
    }
    if (!forced) {
      const step = newStep("update", address, "", 0);
      step.diff = rows;
      return ["update", step];
    }
    for (const name of computed) {
      const old = existing.get(name);
      rows.push(old === undefined ? ["+", name, UNKNOWN] : ["~", name, old, UNKNOWN]);
    }
    const step = newStep("create", address, "replace", 0);
    step.diff = byKey(rows);
    return ["replace", step];
  }

  // Kahn's algorithm, always taking the smallest ready step; the ready list is kept sorted.
  private static order(steps: Step[]): Step[] {
    const smaller = (a: Step, b: Step): number => a.rank - b.rank || compare(a.address, b.address);
    const waiting = new Map(steps.map((step) => [step, step.before.length] as [Step, number]));
    const ready = steps.filter((step) => step.before.length === 0).sort(smaller);
    const order: Step[] = [];
    while (ready.length > 0) {
      const step = ready.shift()!;
      order.push(step);
      for (const later of step.after) {
        waiting.set(later, waiting.get(later)! - 1);
        if (waiting.get(later) === 0) {
          let at = 0;
          while (at < ready.length && smaller(ready[at], later) < 0) {
            at++;
          }
          ready.splice(at, 0, later);
        }
      }
    }
    return order;
  }

  // Applying
  private live(address: string, key: string): string {
    const value = this.desired.get(address)!.get(key)!;
    const target = reference(value);
    if (target === null) {
      return value;
    }
    if (this.isComputed(target[0], target[1])) {
      return this.current.get(target[0])!.get(target[1])!;
    }
    return this.live(target[0], target[1]);
  }

  private built(address: string, assigned: Map<string, string>): Attributes {
    const made: Attributes = new Map();
    for (const key of this.desired.get(address)!.keys()) {
      made.set(key, this.live(address, key));
    }
    for (const name of this.computedOf(address)) {
      made.set(name, assigned.get(`${address} ${name}`)!);
    }
    return made;
  }

  private perform(step: Step, assigned: Map<string, string>): void {
    const address = step.address;
    const needs = new Set<string>();
    for (const value of this.desired.get(address)?.values() ?? []) {
      const target = reference(value);
      if (target !== null) {
        needs.add(target[0]);
      }
    }
    if (step.verb === "create") {
      const existing = this.current.get(address);
      if (step.tag === "replace" && existing !== undefined) {
        this.old.set(address, existing);
        this.oldDeps.set(address, this.deps.get(address) ?? new Set());
      }
      this.current.set(address, this.built(address, assigned));
      this.deps.set(address, needs);
    } else if (step.verb === "update") {
      const made: Attributes = new Map();
      for (const key of this.desired.get(address)!.keys()) {
        made.set(key, this.live(address, key));
      }
      for (const [key, value] of this.current.get(address)!) {
        if (this.isComputed(address, key)) {
          made.set(key, value);
        }
      }
      this.current.set(address, made);
      this.deps.set(address, needs);
    } else if (step.verb === "delete") {
      if (step.tag === "old" || step.mode === CREATE_FIRST) {
        this.old.delete(address);
        this.oldDeps.delete(address);
      } else {
        this.current.delete(address);
        this.deps.delete(address);
      }
    }
  }
}
