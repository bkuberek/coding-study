const SEP = "\u0000";

interface Contract {
  pairs: Array<[string, string]>;
  direct: boolean;
  ignores: Array<[string, string]>;
  exceptions: Map<string, [string, string, string]>;
}

interface Walk {
  order: string[];
  parent: Map<string, string | null>;
}

/**
 * Modules keep the imports as written. The first question after a change resolves every import
 * to the longest declared module that is the import or a dotted prefix of it, and keeps one
 * sorted list of targets per module, so every walk visits neighbours in name order.
 *
 * A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each module
 * first along the shortest chain that is smallest in name order, so one walk per source name
 * answers every pair of a contract that starts there. Cycles are the strongly connected
 * components, found with two depth-first passes over the graph and its reverse.
 */
export class ArchitectureChecker {
  private imports = new Map<string, string[]>();
  private graph: Map<string, string[]> | null = null;
  private contracts = new Map<string, Contract>();
  private version: number[] = [];
  private baseline = new Map<string, string[]>();

  // Level 1
  addModule(name: string, imports: string[]): boolean {
    const isNew = !this.imports.has(name);
    this.imports.set(name, [...imports]);
    this.graph = null;
    return isNew;
  }

  unknownImports(): string[][] {
    const rows = new Map<string, string[]>();
    for (const [module, list] of this.imports) {
      for (const text of list) {
        if (this.resolve(text) === null) rows.set(module + SEP + text, [module, text]);
      }
    }
    return [...rows.values()].sort(compareRows);
  }

  dependencies(name: string): string[] {
    const graph = this.edges();
    const found = new Set<string>();
    for (const module of this.members(name)) {
      for (const target of graph.get(module) ?? []) {
        if (!inside(target, name)) found.add(target);
      }
    }
    return [...found].sort(compareText);
  }

  transitiveDependencies(name: string): string[] {
    const { order, parent } = this.walk(this.members(name), null);
    const depth = new Map<string, number>();
    for (const module of order) {
      const above = parent.get(module);
      depth.set(module, above == null ? 0 : (depth.get(above) ?? 0) + 1);
    }
    return order
      .filter((module) => !inside(module, name))
      .sort((a, b) => (depth.get(a) ?? 0) - (depth.get(b) ?? 0) || compareText(a, b));
  }

  // Level 2
  cycles(depth: number): string[][] {
    const adjacency = new Map<string, Set<string>>();
    for (const [module, targets] of this.edges()) {
      const group = groupOf(module, depth);
      const out = adjacency.get(group) ?? new Set<string>();
      adjacency.set(group, out);
      for (const target of targets) {
        const other = groupOf(target, depth);
        if (other !== group) out.add(other);
      }
    }
    return components(adjacency)
      .filter((part) => part.length > 1)
      .map((part) => part.sort(compareText))
      .sort(compareRows);
  }

  cycleChain(name: string): string[] {
    if (!this.imports.has(name)) return [];
    const graph = this.edges();
    const { order, parent } = this.walk([name], null);
    for (const module of order) {
      if ((graph.get(module) ?? []).includes(name)) return [...chainOf(module, parent), name];
    }
    return [];
  }

  // Level 3
  addLayers(contract: string, layers: string[]): boolean {
    const pairs: Array<[string, string]> = [];
    for (let low = 0; low < layers.length; low++) {
      for (let high = 0; high < low; high++) pairs.push([layers[low], layers[high]]);
    }
    return this.addContract(contract, pairs);
  }

  addForbidden(contract: string, source: string, target: string): boolean {
    return this.addContract(contract, [[source, target]]);
  }

  addIndependence(contract: string, names: string[]): boolean {
    const pairs: Array<[string, string]> = [];
    for (const first of names) {
      for (const second of names) if (first !== second) pairs.push([first, second]);
    }
    return this.addContract(contract, pairs);
  }

  check(): string[][] {
    return this.violations().map(([key, chain]) => [...key, ...chain]);
  }

  // Level 4
  ignore(contract: string, importer: string, imported: string): boolean {
    const rules = this.contracts.get(contract);
    if (rules === undefined) return false;
    if (rules.ignores.some(([a, b]) => a === importer && b === imported)) return false;
    rules.ignores.push([importer, imported]);
    return true;
  }

  allow(contract: string, importer: string, imported: string, until: string): boolean {
    const rules = this.contracts.get(contract);
    if (rules === undefined) return false;
    const key = importer + SEP + imported;
    const old = rules.exceptions.get(key);
    if (old !== undefined && compareVersions(versionKey(old[2]), versionKey(until)) === 0) {
      return false;
    }
    rules.exceptions.set(key, [importer, imported, until]);
    return true;
  }

  setVersion(version: string): string[][] {
    this.version = versionKey(version);
    const rows: string[][] = [];
    for (const [name, rules] of this.contracts) {
      for (const [importer, imported, until] of rules.exceptions.values()) {
        if (compareVersions(versionKey(until), this.version) <= 0) {
          rows.push([name, importer, imported, until]);
        }
      }
    }
    return rows.sort(compareRows);
  }

  setMode(contract: string, mode: string): boolean {
    const rules = this.contracts.get(contract);
    const direct = mode === "direct";
    if (rules === undefined || rules.direct === direct) return false;
    rules.direct = direct;
    return true;
  }

  setBaseline(entries: string[][]): number {
    this.baseline = new Map();
    for (const entry of entries) {
      const key = entry.slice(0, 3);
      this.baseline.set(key.join(SEP), key);
    }
    return this.baseline.size;
  }

  ratchet(): string[][] {
    const current = this.violations();
    const broken = new Set(current.map(([key]) => key.join(SEP)));
    const rows = current
      .filter(([key]) => !this.baseline.has(key.join(SEP)))
      .map(([key, chain]) => ["new", ...key, ...chain]);
    const fixed = [...this.baseline.entries()]
      .filter(([key]) => !broken.has(key))
      .map(([, entry]) => entry)
      .sort(compareRows);
    for (const entry of fixed) this.baseline.delete(entry.join(SEP));
    return [...rows, ...fixed.map((entry) => ["fixed", ...entry])];
  }

  // Helpers
  private resolve(text: string): string | null {
    let name = text;
    while (!this.imports.has(name)) {
      const cut = name.lastIndexOf(".");
      if (cut < 0) return null;
      name = name.slice(0, cut);
    }
    return name;
  }

  private edges(): Map<string, string[]> {
    if (this.graph === null) {
      const graph = new Map<string, string[]>();
      for (const [module, list] of this.imports) {
        const targets = new Set<string>();
        for (const text of list) {
          const target = this.resolve(text);
          if (target !== null && target !== module) targets.add(target);
        }
        graph.set(module, [...targets].sort(compareText));
      }
      this.graph = graph;
    }
    return this.graph;
  }

  private members(name: string): string[] {
    return [...this.imports.keys()].filter((module) => inside(module, name)).sort(compareText);
  }

  /** Breadth-first from the sorted starts over sorted neighbours; `order` is also the queue. */
  private walk(starts: string[], rules: Contract | null): Walk {
    const graph = this.edges();
    const parent = new Map<string, string | null>();
    for (const start of starts) parent.set(start, null);
    const order = [...starts];
    for (let head = 0; head < order.length; head++) {
      const module = order[head];
      for (const target of graph.get(module) ?? []) {
        if (!parent.has(target) && !this.skipped(rules, module, target)) {
          parent.set(target, module);
          order.push(target);
        }
      }
    }
    return { order, parent };
  }

  private addContract(contract: string, pairs: Array<[string, string]>): boolean {
    if (this.contracts.has(contract)) return false;
    this.contracts.set(contract, { pairs, direct: false, ignores: [], exceptions: new Map() });
    return true;
  }

  private skipped(rules: Contract | null, importer: string, imported: string): boolean {
    if (rules === null) return false;
    for (const [a, b] of rules.ignores) {
      if (inside(importer, a) && inside(imported, b)) return true;
    }
    for (const [a, b, until] of rules.exceptions.values()) {
      const live = compareVersions(this.version, versionKey(until)) < 0;
      if (live && inside(importer, a) && inside(imported, b)) return true;
    }
    return false;
  }

  private violations(): Array<[string[], string[]]> {
    const found: Array<[string[], string[]]> = [];
    for (const name of [...this.contracts.keys()].sort(compareText)) {
      const rules = this.contracts.get(name) as Contract;
      const sources = [...new Set(rules.pairs.map(([from]) => from))].sort(compareText);
      for (const source of sources) {
        const targets = rules.pairs.filter(([from]) => from === source).map(([, to]) => to);
        for (const [target, chain] of this.chains(rules, source, targets)) {
          found.push([[name, source, target], chain]);
        }
      }
    }
    return found.sort((a, b) => compareRows(a[0], b[0]));
  }

  private chains(rules: Contract, source: string, targets: string[]): Array<[string, string[]]> {
    const starts = this.members(source);
    const found: Array<[string, string[]]> = [];
    if (rules.direct) {
      for (const target of targets) {
        const pair = this.firstImport(rules, starts, target);
        if (pair !== null) found.push([target, pair]);
      }
      return found;
    }
    const { order, parent } = this.walk(starts, rules);
    for (const target of targets) {
      const first = order.find((module) => inside(module, target));
      if (first !== undefined) found.push([target, chainOf(first, parent)]);
    }
    return found;
  }

  /** The starts and their targets are sorted, so the first import found is the smallest. */
  private firstImport(rules: Contract, starts: string[], target: string): string[] | null {
    const graph = this.edges();
    for (const module of starts) {
      for (const other of graph.get(module) ?? []) {
        if (inside(other, target) && !this.skipped(rules, module, other)) return [module, other];
      }
    }
    return null;
  }
}

function inside(module: string, name: string): boolean {
  return module === name || module.startsWith(name + ".");
}

function groupOf(module: string, depth: number): string {
  return depth === 0 ? module : module.split(".").slice(0, depth).join(".");
}

function chainOf(module: string, parent: Map<string, string | null>): string[] {
  const chain: string[] = [];
  let step: string | null | undefined = module;
  while (step != null) {
    chain.push(step);
    step = parent.get(step);
  }
  return chain.reverse();
}

function versionKey(text: string): number[] {
  const parts = text.split(".").map(Number);
  while (parts.length > 0 && parts[parts.length - 1] === 0) parts.pop();
  return parts;
}

function compareVersions(a: number[], b: number[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return a.length - b.length;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareRows(a: readonly string[], b: readonly string[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const order = compareText(a[i], b[i]);
    if (order !== 0) return order;
  }
  return a.length - b.length;
}

/** Two depth-first passes: finishing order on the graph, then components on its reverse. */
function components(adjacency: Map<string, Set<string>>): string[][] {
  const nodes = [...adjacency.keys()].sort(compareText);
  const forward = new Map<string, string[]>();
  const reverse = new Map<string, string[]>();
  for (const node of nodes) {
    forward.set(node, [...(adjacency.get(node) ?? [])].sort(compareText));
    reverse.set(node, []);
  }
  for (const node of nodes) {
    for (const target of forward.get(node) ?? []) reverse.get(target)?.push(node);
  }
  const finished: string[] = [];
  const seen = new Set<string>();
  for (const root of nodes) {
    if (seen.has(root)) continue;
    seen.add(root);
    const stack: Array<[string, number]> = [[root, 0]];
    while (stack.length > 0) {
      const top = stack[stack.length - 1];
      const next = forward.get(top[0]) ?? [];
      if (top[1] < next.length) {
        const target = next[top[1]];
        top[1] += 1;
        if (!seen.has(target)) {
          seen.add(target);
          stack.push([target, 0]);
        }
      } else {
        stack.pop();
        finished.push(top[0]);
      }
    }
  }
  const assigned = new Set<string>();
  const parts: string[][] = [];
  for (let i = finished.length - 1; i >= 0; i--) {
    const root = finished[i];
    if (assigned.has(root)) continue;
    assigned.add(root);
    const part: string[] = [];
    const stack = [root];
    while (stack.length > 0) {
      const node = stack.pop() as string;
      part.push(node);
      for (const source of reverse.get(node) ?? []) {
        if (!assigned.has(source)) {
          assigned.add(source);
          stack.push(source);
        }
      }
    }
    parts.push(part);
  }
  return parts;
}
