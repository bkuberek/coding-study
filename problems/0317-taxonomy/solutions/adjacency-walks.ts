// Every concept keeps the set of its parents and the set of its children. Questions about
// ancestors, descendants, cycles and expansion are breadth-first walks over those sets, so
// nothing recurses and a chain of 10^5 concepts is as safe as a flat list.
// Retired concepts keep their id and their labels; a table of replacements sends them to a live
// concept, and every method that takes an id first follows that table.
export class Taxonomy {
  private label = new Map<string, string>();
  private up = new Map<string, Set<string>>();
  private down = new Map<string, Set<string>>();
  private alts = new Map<string, string[]>();
  private index = new Map<string, Set<string>>();
  private gone = new Map<string, string>();
  private same = new Map<string, Set<string>>();

  // Level 1
  addConcept(concept: string, label: string, parents: string[]): string {
    if (this.label.has(concept)) return "duplicate";
    if (parents.includes(concept)) return "cycle";
    if (parents.some((parent) => !this.label.has(parent))) return "unknown-broader";
    const resolved = new Set(parents.map((parent) => this.follow(parent)));
    for (const parent of resolved) {
      if (this.scheme(parent) !== this.scheme(concept)) return "cross-scheme";
    }
    this.label.set(concept, label);
    this.up.set(concept, resolved);
    this.down.set(concept, new Set());
    this.alts.set(concept, []);
    this.same.set(concept, new Set());
    for (const parent of resolved) this.down.get(parent)!.add(concept);
    this.indexLabel(concept, label);
    return "ok";
  }

  addBroader(narrower: string, broader: string): string {
    const child = this.follow(narrower);
    const parent = this.follow(broader);
    if (!this.label.has(child) || !this.label.has(parent)) return "unknown-concept";
    if (this.scheme(child) !== this.scheme(parent)) return "cross-scheme";
    if (child === parent || this.reach(parent, this.up).has(child)) return "cycle";
    this.up.get(child)!.add(parent);
    this.down.get(parent)!.add(child);
    return "ok";
  }

  prefLabel(concept: string): string {
    return this.label.get(this.follow(concept)) ?? "";
  }

  broader(concept: string): string[] {
    return [...(this.up.get(this.follow(concept)) ?? [])].sort();
  }

  narrower(concept: string): string[] {
    return [...(this.down.get(this.follow(concept)) ?? [])].sort();
  }

  ancestors(concept: string): string[] {
    return this.nearestFirst(this.follow(concept), this.up);
  }

  descendants(concept: string): string[] {
    return this.nearestFirst(this.follow(concept), this.down);
  }

  roots(): string[] {
    const found: string[] = [];
    for (const [concept, parents] of this.up) {
      if (!this.gone.has(concept) && parents.size === 0) found.push(concept);
    }
    return found.sort();
  }

  // Level 2
  lowestCommonAncestors(first: string, second: string): string[] {
    const a = this.follow(first);
    const b = this.follow(second);
    if (!this.label.has(a) || !this.label.has(b)) return [];
    const aboveB = this.reach(b, this.up);
    const common = new Set([...this.reach(a, this.up)].filter((c) => aboveB.has(c)));
    const lowest = [...common].filter((c) => ![...this.down.get(c)!].some((kid) => common.has(kid)));
    return lowest.sort();
  }

  // Level 3
  addAltLabel(concept: string, label: string): string {
    const id = this.follow(concept);
    if (!this.label.has(id)) return "unknown-concept";
    const key = this.normalize(label);
    if (key === "") return "empty-label";
    const own = [this.label.get(id)!, ...this.alts.get(id)!].map((text) => this.normalize(text));
    if (own.includes(key)) return "duplicate";
    this.alts.get(id)!.push(label);
    this.indexLabel(id, label);
    return "ok";
  }

  altLabels(concept: string): string[] {
    return [...(this.alts.get(this.follow(concept)) ?? [])];
  }

  findByLabel(label: string): string[] {
    return [...this.matching(label)].sort();
  }

  expand(labels: string[]): string[] {
    const seen = new Set<string>();
    const queue: string[] = [];
    for (const label of labels) {
      for (const concept of this.matching(label)) {
        if (!seen.has(concept)) {
          seen.add(concept);
          queue.push(concept);
        }
      }
    }
    for (let next = 0; next < queue.length; next++) {
      for (const kid of this.down.get(queue[next])!) {
        if (!seen.has(kid)) {
          seen.add(kid);
          queue.push(kid);
        }
      }
    }
    return [...seen].sort();
  }

  // Level 4
  rename(concept: string, label: string): string {
    const id = this.follow(concept);
    if (!this.label.has(id)) return "unknown-concept";
    const old = this.label.get(id)!;
    const key = this.normalize(label);
    const kept = this.alts.get(id)!.filter((text) => this.normalize(text) !== key);
    const oldKey = this.normalize(old);
    if (oldKey !== "" && oldKey !== key) kept.push(old);
    this.alts.set(id, kept);
    this.label.set(id, label);
    this.indexLabel(id, label);
    return "ok";
  }

  removeBroader(narrower: string, broader: string): string {
    const child = this.follow(narrower);
    const parent = this.follow(broader);
    if (!this.label.has(child) || !this.label.has(parent)) return "unknown-concept";
    if (!this.up.get(child)!.has(parent)) return "no-link";
    this.up.get(child)!.delete(parent);
    this.down.get(parent)!.delete(child);
    return "ok";
  }

  deprecate(concept: string, replacement: string): string {
    if (!this.label.has(concept) || !this.label.has(replacement)) return "unknown-concept";
    if (this.gone.has(concept)) return "deprecated";
    const target = this.follow(replacement);
    if (target === concept) return "same-concept";
    if (this.scheme(target) !== this.scheme(concept)) return "cross-scheme";
    if (this.down.get(concept)!.size > 0) return "has-narrower";
    for (const parent of this.up.get(concept)!) this.down.get(parent)!.delete(concept);
    this.up.set(concept, new Set());
    for (const partner of this.same.get(concept)!) {
      this.same.get(partner)!.delete(concept);
      this.same.get(partner)!.add(target);
      this.same.get(target)!.add(partner);
    }
    this.same.set(concept, new Set());
    this.gone.set(concept, target);
    return "ok";
  }

  resolve(concept: string): string {
    const id = this.follow(concept);
    return this.label.has(id) ? id : "";
  }

  addExactMatch(first: string, second: string): string {
    const a = this.follow(first);
    const b = this.follow(second);
    if (!this.label.has(a) || !this.label.has(b)) return "unknown-concept";
    if (this.scheme(a) === this.scheme(b)) return "same-scheme";
    this.same.get(a)!.add(b);
    this.same.get(b)!.add(a);
    return "ok";
  }

  translate(concepts: string[], scheme: string): string[] {
    const found = new Set<string>();
    for (const concept of this.known(concepts)) {
      for (const target of this.targets(concept, scheme)) found.add(target);
    }
    return [...found].sort();
  }

  unmapped(concepts: string[], scheme: string): string[] {
    return this.known(concepts).filter((concept) => this.targets(concept, scheme).length === 0);
  }

  // Helpers
  private scheme(concept: string): string {
    const colon = concept.indexOf(":");
    return colon < 0 ? "" : concept.slice(0, colon);
  }

  // Trim the spaces at both ends, turn each run of spaces into one, lower-case A to Z.
  private normalize(label: string): string {
    return label
      .split(" ")
      .filter((part) => part !== "")
      .join(" ")
      .toLowerCase();
  }

  private follow(concept: string): string {
    let current = concept;
    while (this.gone.has(current)) current = this.gone.get(current)!;
    if (current !== concept) this.gone.set(concept, current);
    return current;
  }

  private known(concepts: string[]): string[] {
    const resolved = new Set(concepts.map((concept) => this.follow(concept)));
    return [...resolved].filter((concept) => this.label.has(concept)).sort();
  }

  private targets(concept: string, scheme: string): string[] {
    if (this.scheme(concept) === scheme) return [concept];
    return [...this.same.get(concept)!].filter((partner) => this.scheme(partner) === scheme);
  }

  private indexLabel(concept: string, label: string): void {
    const key = this.normalize(label);
    if (key === "") return;
    const holders = this.index.get(key);
    if (holders === undefined) this.index.set(key, new Set([concept]));
    else holders.add(concept);
  }

  private matching(label: string): Set<string> {
    const key = this.normalize(label);
    const found = new Set<string>();
    if (key === "") return found;
    for (const concept of this.index.get(key) ?? []) found.add(this.follow(concept));
    return found;
  }

  // The concept itself and everything above (or below) it.
  private reach(start: string, edges: Map<string, Set<string>>): Set<string> {
    const seen = new Set([start]);
    const queue = [start];
    for (let next = 0; next < queue.length; next++) {
      for (const neighbour of edges.get(queue[next])!) {
        if (!seen.has(neighbour)) {
          seen.add(neighbour);
          queue.push(neighbour);
        }
      }
    }
    return seen;
  }

  private nearestFirst(start: string, edges: Map<string, Set<string>>): string[] {
    if (!edges.has(start)) return [];
    const seen = new Set([start]);
    let level = [start];
    const found: string[] = [];
    while (level.length > 0) {
      const following = new Set<string>();
      for (const current of level) {
        for (const neighbour of edges.get(current)!) {
          if (!seen.has(neighbour)) following.add(neighbour);
        }
      }
      for (const concept of following) seen.add(concept);
      level = [...following].sort();
      for (const concept of level) found.push(concept);
    }
    return found;
  }
}
