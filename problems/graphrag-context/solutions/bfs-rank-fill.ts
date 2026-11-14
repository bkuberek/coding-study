const HOP_BASE = 16;
const RECENCY_BASE = 16;
const MAX_RECENCY_STEPS = 4;
const CHARACTERS_PER_TOKEN = 4;

class Fact {
  readonly subject: string;
  readonly relation: string;
  readonly object: string;
  readonly weight: number;
  readonly time: number;

  constructor(subject: string, relation: string, object: string, weight: number, time: number) {
    this.subject = subject;
    this.relation = relation;
    this.object = object;
    this.weight = weight;
    this.time = time;
  }

  /** The characters of 'subject relation object', in groups of 4, rounded up. */
  tokens(): number {
    const characters = this.subject.length + this.relation.length + this.object.length + 2;
    return Math.ceil(characters / CHARACTERS_PER_TOKEN);
  }

  row(): string[] {
    return [this.subject, this.relation, this.object];
  }

  other(node: string): string {
    return this.subject === node ? this.object : this.subject;
  }
}

interface Ranked {
  fact: Fact;
  hop: number;
  score: number;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareFacts(a: Fact, b: Fact): number {
  return compareText(a.subject, b.subject) || compareText(a.relation, b.relation) || compareText(a.object, b.object);
}

export class GraphContext {
  private readonly facts = new Map<string, Fact>();
  private readonly incident = new Map<string, Fact[]>();

  // Level 1
  addFact(subject: string, relation: string, obj: string, weight: number, time: number): boolean {
    const key = [subject, relation, obj].join("\u0000");
    if (this.facts.has(key)) {
      return false;
    }
    const fact = new Fact(subject, relation, obj, weight, time);
    this.facts.set(key, fact);
    this.attach(subject, fact);
    if (obj !== subject) {
      this.attach(obj, fact);
    }
    return true;
  }

  size(): number {
    return this.facts.size;
  }

  egoNetwork(entity: string, hops: number): string[][] {
    return this.within(entity, hops).map(({ fact, hop }) => [...fact.row(), String(hop)]);
  }

  // Level 2
  rankFacts(entity: string, hops: number, now: number, halfLife: number): string[][] {
    return this.ranked(entity, hops, now, halfLife).map(({ fact, hop, score }) => [
      ...fact.row(),
      String(hop),
      String(score),
    ]);
  }

  // Level 3
  buildContext(entity: string, hops: number, now: number, halfLife: number, budget: number): string[][] {
    return this.packed(entity, hops, now, halfLife, budget).map(({ fact, hop, score }) => [
      ...fact.row(),
      String(hop),
      String(score),
      String(fact.tokens()),
    ]);
  }

  // Level 4
  explain(entity: string, subject: string, relation: string, obj: string): string[][] {
    const fact = this.facts.get([subject, relation, obj].join("\u0000"));
    if (fact === undefined) {
      return [];
    }
    return this.path(this.distances(entity), entity, fact).map((step) => step.row());
  }

  renderContext(entity: string, hops: number, now: number, halfLife: number, budget: number): string {
    const chosen = this.packed(entity, hops, now, halfLife, budget);
    const used = chosen.reduce((total, { fact }) => total + fact.tokens(), 0);
    const lines = [`Context for ${entity} (${chosen.length} facts, ${used} of ${budget} tokens)`];
    const distances = this.distances(entity);
    chosen.forEach(({ fact }, index) => {
      const text = pathText(entity, this.path(distances, entity, fact));
      lines.push(`[${index + 1}] ${fact.row().join(" ")} | path: ${text}`);
    });
    return lines.join("\n");
  }

  // Helpers
  private attach(node: string, fact: Fact): void {
    const list = this.incident.get(node);
    if (list === undefined) {
      this.incident.set(node, [fact]);
    } else {
      list.push(fact);
    }
  }

  private distances(entity: string): Map<string, number> {
    const distance = new Map<string, number>();
    if (!this.incident.has(entity)) {
      return distance;
    }
    distance.set(entity, 0);
    const queue = [entity];
    for (let head = 0; head < queue.length; head++) {
      const node = queue[head];
      for (const fact of this.incident.get(node) ?? []) {
        for (const other of [fact.subject, fact.object]) {
          if (!distance.has(other)) {
            distance.set(other, (distance.get(node) as number) + 1);
            queue.push(other);
          }
        }
      }
    }
    return distance;
  }

  private within(entity: string, hops: number): { fact: Fact; hop: number }[] {
    const distance = this.distances(entity);
    const found: { fact: Fact; hop: number }[] = [];
    for (const fact of this.facts.values()) {
      const nearest = Math.min(distance.get(fact.subject) ?? hops, distance.get(fact.object) ?? hops);
      if (nearest < hops) {
        found.push({ fact, hop: nearest + 1 });
      }
    }
    return found.sort((a, b) => a.hop - b.hop || compareFacts(a.fact, b.fact));
  }

  private score(fact: Fact, hop: number, now: number, halfLife: number): number {
    const steps = Math.min(MAX_RECENCY_STEPS, Math.floor(Math.max(0, now - fact.time) / halfLife));
    return fact.weight * (HOP_BASE >> (hop - 1)) * (RECENCY_BASE >> steps);
  }

  private ranked(entity: string, hops: number, now: number, halfLife: number): Ranked[] {
    return this.within(entity, hops)
      .map(({ fact, hop }) => ({ fact, hop, score: this.score(fact, hop, now, halfLife) }))
      .sort((a, b) => b.score - a.score || a.hop - b.hop || compareFacts(a.fact, b.fact));
  }

  private packed(entity: string, hops: number, now: number, halfLife: number, budget: number): Ranked[] {
    let remaining = budget;
    const chosen: Ranked[] = [];
    for (const item of this.ranked(entity, hops, now, halfLife)) {
      const tokens = item.fact.tokens();
      if (tokens <= remaining) {
        chosen.push(item);
        remaining -= tokens;
      }
    }
    return chosen;
  }

  /** The step into `node` from one step closer: the smallest such neighbour, by its smallest fact. */
  private parent(distances: Map<string, number>, node: string): { node: string; fact: Fact } {
    const wanted = (distances.get(node) as number) - 1;
    let best: { node: string; fact: Fact } | null = null;
    for (const fact of this.incident.get(node) ?? []) {
      const other = fact.other(node);
      if (distances.get(other) !== wanted) {
        continue;
      }
      if (best === null || compareText(other, best.node) < 0 || (other === best.node && compareFacts(fact, best.fact) < 0)) {
        best = { node: other, fact };
      }
    }
    return best as { node: string; fact: Fact };
  }

  private path(distances: Map<string, number>, entity: string, fact: Fact): Fact[] {
    const reachable = [fact.subject, fact.object].filter((node) => distances.has(node));
    if (reachable.length === 0) {
      return [];
    }
    const near = reachable.reduce((best, node) => {
      const nearer = (distances.get(node) as number) - (distances.get(best) as number);
      return nearer < 0 || (nearer === 0 && compareText(node, best) < 0) ? node : best;
    });
    const steps: Fact[] = [];
    let node = near;
    while (node !== entity) {
      const step = this.parent(distances, node);
      steps.push(step.fact);
      node = step.node;
    }
    steps.reverse();
    return [...steps, fact];
  }
}

function pathText(entity: string, path: Fact[]): string {
  let text = entity;
  let node = entity;
  for (const step of path) {
    if (node === step.subject) {
      text += ` -${step.relation}-> ${step.object}`;
      node = step.object;
    } else {
      text += ` <-${step.relation}- ${step.subject}`;
      node = step.subject;
    }
  }
  return text;
}
