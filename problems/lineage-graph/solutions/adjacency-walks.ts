const USAGES = new Set(["identity", "transform", "aggregate", "filter"]);
const MASKABLE = new Set(["transform", "aggregate"]);

interface Edge {
  source: string;
  target: string;
  usage: string;
  masking: boolean;
}

const everyEdge = (_: Edge): boolean => true;
const identityOnly = (edge: Edge): boolean => edge.usage === "identity";
const carriesValue = (edge: Edge): boolean => edge.usage !== "filter" && !edge.masking;

// A dataset or column name: 1 to 20 characters from a-z, 0-9 and _.
function isName(text: string): boolean {
  if (text.length < 1 || text.length > 20) {
    return false;
  }
  for (const ch of text) {
    if (!((ch >= "a" && ch <= "z") || (ch >= "0" && ch <= "9") || ch === "_")) {
      return false;
    }
  }
  return true;
}

function isColumnRef(text: string): boolean {
  const parts = text.split(".");
  return parts.length === 2 && parts.every(isName);
}

function datasetOf(column: string): string {
  return column.split(".")[0];
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareRows(a: string[], b: string[]): number {
  for (let at = 0; at < Math.min(a.length, b.length); at++) {
    const order = compareText(a[at], b[at]);
    if (order !== 0) {
      return order;
    }
  }
  return a.length - b.length;
}

// Columns are nodes named dataset.column, and each lineage edge points from an input column to
// the column computed from it. Two adjacency maps, forward and backward, answer every walk: a
// breadth-first search gives distances for the ordered queries, a filter on the edge's usage
// restricts a walk to the edges a change or a label travels along, and Kosaraju's two passes group
// the columns that sit on a cycle.
export class LineageGraph {
  private columns = new Map<string, string[]>();
  private edges: Edge[] = [];
  private forward = new Map<string, Edge[]>();
  private backward = new Map<string, Edge[]>();
  private labels = new Map<string, Set<string>>();
  private published = new Set<string>();

  // Level 1
  addDataset(name: string, columns: string[], edges: string[][]): boolean {
    if (this.columns.has(name) || !isName(name) || !columns.every(isName) || new Set(columns).size !== columns.length) {
      return false;
    }
    const pairs = new Set<string>();
    const parsed: Edge[] = [];
    for (const edge of edges) {
      if (edge.length < 3 || edge.length > 4 || !columns.includes(edge[0]) || !isColumnRef(edge[1])) {
        return false;
      }
      const usage = edge[2];
      const masking = edge.length === 4;
      if (!USAGES.has(usage) || (masking && (edge[3] !== "masking" || !MASKABLE.has(usage)))) {
        return false;
      }
      const pair = `${edge[0]} ${edge[1]}`;
      if (pairs.has(pair)) {
        return false;
      }
      pairs.add(pair);
      parsed.push({ source: edge[1], target: `${name}.${edge[0]}`, usage, masking });
    }
    this.columns.set(name, [...columns]);
    for (const edge of parsed) {
      this.edges.push(edge);
      this.listOf(this.forward, edge.source).push(edge);
      this.listOf(this.backward, edge.target).push(edge);
    }
    return true;
  }

  validate(): string[][] {
    const issues: string[][] = [];
    for (const edge of this.edges) {
      const [dataset, column] = edge.source.split(".");
      const declared = this.columns.get(dataset);
      if (declared === undefined) {
        issues.push(["unknown-dataset", edge.target, edge.source]);
      } else if (!declared.includes(column)) {
        issues.push(["unknown-column", edge.target, edge.source]);
      }
    }
    for (const group of this.cycles()) {
      issues.push(["cycle", ...group]);
    }
    return issues.sort(compareRows);
  }

  inputsOf(column: string): string[] {
    return (this.backward.get(column) ?? []).map((edge) => edge.source).sort(compareText);
  }

  // Level 2
  upstream(column: string): string[] {
    return this.byDistance(this.walk(column, false, everyEdge));
  }

  downstream(column: string): string[] {
    return this.byDistance(this.walk(column, true, everyEdge));
  }

  // Level 3
  impact(column: string, change: string): string[][] {
    const reached = this.affected(column, change);
    return this.byDistance(reached).map((name) => [name, reached.get(name) === 1 ? "direct" : "derived"]);
  }

  isBreaking(column: string, change: string): boolean {
    if (change !== "retype") {
      return this.affected(column, change).size > 0;
    }
    const typed = this.typed(column);
    return [...typed.keys()].some((name) => (this.forward.get(name) ?? []).some((edge) => edge.usage !== "identity"));
  }

  impactedDatasets(column: string, change: string): string[] {
    return [...new Set([...this.affected(column, change).keys()].map(datasetOf))].sort(compareText);
  }

  // Level 4
  tag(column: string, label: string): boolean {
    if (!this.declared(column) || (this.labels.get(column)?.has(label) ?? false)) {
      return false;
    }
    if (!this.labels.has(column)) {
      this.labels.set(column, new Set());
    }
    (this.labels.get(column) as Set<string>).add(label);
    return true;
  }

  tagsOf(column: string): string[] {
    const sources = this.walk(column, false, carriesValue);
    sources.set(column, 0);
    const found = new Set<string>();
    for (const name of sources.keys()) {
      this.labels.get(name)?.forEach((label) => found.add(label));
    }
    return [...found].sort(compareText);
  }

  publish(dataset: string): boolean {
    if (!this.columns.has(dataset) || this.published.has(dataset)) {
      return false;
    }
    this.published.add(dataset);
    return true;
  }

  exposures(label: string): string[][] {
    const found: string[][] = [];
    for (const [source, labels] of this.labels) {
      if (!labels.has(label)) {
        continue;
      }
      const reached = this.walk(source, true, carriesValue);
      reached.set(source, 0);
      for (const name of reached.keys()) {
        if (this.published.has(datasetOf(name))) {
          found.push([name, source]);
        }
      }
    }
    return found.sort(compareRows);
  }

  // Helpers
  private listOf(map: Map<string, Edge[]>, column: string): Edge[] {
    let list = map.get(column);
    if (list === undefined) {
      list = [];
      map.set(column, list);
    }
    return list;
  }

  private declared(column: string): boolean {
    if (!isColumnRef(column)) {
      return false;
    }
    const [dataset, name] = column.split(".");
    return this.columns.get(dataset)?.includes(name) ?? false;
  }

  // Breadth-first distances from start along the kept edges; start itself is in the answer only
  // when an edge leads back to it.
  private walk(start: string, forward: boolean, keep: (edge: Edge) => boolean): Map<string, number> {
    const distance = new Map<string, number>();
    const queue: [string, number][] = [[start, 0]];
    for (let head = 0; head < queue.length; head++) {
      const [node, steps] = queue[head];
      const edges = (forward ? this.forward : this.backward).get(node) ?? [];
      for (const edge of edges) {
        const next = forward ? edge.target : edge.source;
        if (keep(edge) && !distance.has(next)) {
          distance.set(next, steps + 1);
          queue.push([next, steps + 1]);
        }
      }
    }
    return distance;
  }

  private typed(column: string): Map<string, number> {
    const typed = this.walk(column, true, identityOnly);
    typed.set(column, 0);
    return typed;
  }

  private affected(column: string, change: string): Map<string, number> {
    if (change === "drop") {
      return this.walk(column, true, everyEdge);
    }
    if (change === "rename") {
      return new Map((this.forward.get(column) ?? []).map((edge) => [edge.target, 1]));
    }
    const affected = new Map<string, number>();
    for (const [name, steps] of this.typed(column)) {
      for (const edge of this.forward.get(name) ?? []) {
        const known = affected.get(edge.target);
        if (known === undefined || steps + 1 < known) {
          affected.set(edge.target, steps + 1);
        }
      }
    }
    return affected;
  }

  private byDistance(distance: Map<string, number>): string[] {
    return [...distance.keys()].sort(
      (a, b) => (distance.get(a) as number) - (distance.get(b) as number) || compareText(a, b),
    );
  }

  // Strongly connected groups that hold a cycle, by Kosaraju's two passes.
  private cycles(): string[][] {
    const nodes = [...new Set(this.edges.flatMap((edge) => [edge.source, edge.target]))].sort(compareText);
    const finished: string[] = [];
    const seen = new Set<string>();
    for (const root of nodes) {
      if (seen.has(root)) {
        continue;
      }
      seen.add(root);
      const stack: [string, number][] = [[root, 0]];
      while (stack.length > 0) {
        const top = stack[stack.length - 1];
        const edges = this.forward.get(top[0]) ?? [];
        if (top[1] === edges.length) {
          stack.pop();
          finished.push(top[0]);
          continue;
        }
        const next = edges[top[1]++].target;
        if (!seen.has(next)) {
          seen.add(next);
          stack.push([next, 0]);
        }
      }
    }
    const grouped = new Set<string>();
    const groups: string[][] = [];
    for (let at = finished.length - 1; at >= 0; at--) {
      const root = finished[at];
      if (grouped.has(root)) {
        continue;
      }
      grouped.add(root);
      const members = [root];
      const pending = [root];
      while (pending.length > 0) {
        const node = pending.pop() as string;
        for (const edge of this.backward.get(node) ?? []) {
          if (!grouped.has(edge.source)) {
            grouped.add(edge.source);
            members.push(edge.source);
            pending.push(edge.source);
          }
        }
      }
      groups.push(members.sort(compareText));
    }
    const selfLoops = new Set(this.edges.filter((edge) => edge.source === edge.target).map((edge) => edge.source));
    return groups.filter((group) => group.length > 1 || selfLoops.has(group[0]));
  }
}
