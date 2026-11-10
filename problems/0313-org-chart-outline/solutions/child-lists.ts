// Rows are indexed once by id, then every question is a walk over the index.
// Nothing here recurses: the outline and the subtree sizes use an explicit stack and a
// breadth-first order, so a chain of 10^5 managers is as safe as a flat one.
export class OrgChart {
  private ids: string[] = [];
  private parents = new Map<string, string>();
  private names = new Map<string, string>();
  private kids = new Map<string, string[]>();
  private orphanIds: string[] = [];
  private tops: string[] = [];
  private attached = new Set<string>();
  private sizes = new Map<string, number>();
  private cycleList: string[][] = [];

  // Level 1
  load(rows: string[][]): void {
    this.ids = rows.map((row) => row[0]);
    this.parents = new Map(rows.map((row) => [row[0], row[1]]));
    this.names = new Map(rows.map((row) => [row[0], row[2]]));
    this.kids = new Map();
    for (const [id, parent] of rows) {
      const siblings = this.kids.get(parent);
      if (siblings === undefined) {
        this.kids.set(parent, [id]);
      } else {
        siblings.push(id);
      }
    }
    this.orphanIds = this.ids.filter((id) => this.parents.get(id) !== "" && !this.names.has(this.parents.get(id) as string));
    const orphanSet = new Set(this.orphanIds);
    this.tops = this.ids.filter((id) => this.parents.get(id) === "" || orphanSet.has(id));
    const order = [...this.tops];
    this.attached = new Set(order);
    for (let next = 0; next < order.length; next++) {
      for (const kid of this.kids.get(order[next]) ?? []) {
        this.attached.add(kid);
        order.push(kid);
      }
    }
    this.sizes = new Map(order.map((id) => [id, 1]));
    for (let at = order.length - 1; at >= 0; at--) {
      const parent = this.parents.get(order[at]) as string;
      const parentSize = this.sizes.get(parent);
      if (parentSize !== undefined) {
        this.sizes.set(parent, parentSize + (this.sizes.get(order[at]) as number));
      }
    }
    this.cycleList = this.findCycles();
  }

  roots(): string[] {
    return [...(this.kids.get("") ?? [])];
  }

  nameOf(employee: string): string {
    return this.names.get(employee) ?? "";
  }

  children(employee: string): string[] {
    return this.names.has(employee) ? [...(this.kids.get(employee) ?? [])] : [];
  }

  // Level 2
  orphans(): string[] {
    return [...this.orphanIds];
  }

  cycles(): string[][] {
    return this.cycleList.map((cycle) => [...cycle]);
  }

  // Level 3
  chain(employee: string): string[] {
    if (!this.attached.has(employee)) {
      return [];
    }
    const path = [employee];
    let parent = this.parents.get(employee) as string;
    while (this.names.has(parent)) {
      path.push(parent);
      parent = this.parents.get(parent) as string;
    }
    return path;
  }

  lowestCommonManager(first: string, second: string): string {
    const aboveSecond = new Set(this.chain(second));
    for (const manager of this.chain(first)) {
      if (aboveSecond.has(manager)) {
        return manager;
      }
    }
    return "";
  }

  // Level 4
  subtreeSize(employee: string): number {
    return this.sizes.get(employee) ?? 0;
  }

  outline(order: string): string[] {
    const lines: string[] = [];
    const stack: [string, number][] = this.sorted(this.tops, order)
      .reverse()
      .map((top) => [top, 0]);
    while (stack.length > 0) {
      const [current, depth] = stack.pop() as [string, number];
      lines.push(`${"  ".repeat(depth)}${this.names.get(current)} (${current})`);
      const below = this.sorted(this.kids.get(current) ?? [], order);
      for (let at = below.length - 1; at >= 0; at--) {
        stack.push([below[at], depth + 1]);
      }
    }
    return lines;
  }

  private sorted(ids: string[], order: string): string[] {
    const copy = [...ids];
    if (order === "name") {
      return copy.sort((a, b) => this.compare(this.names.get(a) as string, this.names.get(b) as string) || this.compare(a, b));
    }
    if (order === "size") {
      return copy.sort(
        (a, b) =>
          (this.sizes.get(b) as number) - (this.sizes.get(a) as number) ||
          this.compare(this.names.get(a) as string, this.names.get(b) as string) ||
          this.compare(a, b),
      );
    }
    return copy;
  }

  private compare(a: string, b: string): number {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  private findCycles(): string[][] {
    const position = new Map(this.ids.map((id, index) => [id, index]));
    const seen = new Set(this.attached);
    const found: string[][] = [];
    for (const start of this.ids) {
      const walk: string[] = [];
      let current = start;
      while (!seen.has(current)) {
        seen.add(current);
        walk.push(current);
        current = this.parents.get(current) as string;
      }
      const at = walk.indexOf(current);
      if (at >= 0) {
        const cycle = walk.slice(at);
        let first = 0;
        for (let k = 1; k < cycle.length; k++) {
          if ((position.get(cycle[k]) as number) < (position.get(cycle[first]) as number)) {
            first = k;
          }
        }
        found.push([...cycle.slice(first), ...cycle.slice(0, first)]);
      }
    }
    return found.sort((a, b) => (position.get(a[0]) as number) - (position.get(b[0]) as number));
  }
}
