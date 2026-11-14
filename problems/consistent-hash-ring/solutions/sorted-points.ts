const RING_SIZE = 2 ** 32;
const FNV_OFFSET_BASIS = 2166136261;
const FNV_PRIME = 16777619;
const encoder = new TextEncoder();

// FNV-1a, 32 bits, over the UTF-8 bytes of the text. Math.imul multiplies in 32 bits, and
// `>>> 0` reads the result as unsigned.
function fnv1a(text: string): number {
  let value = FNV_OFFSET_BASIS;
  for (const byte of encoder.encode(text)) value = Math.imul(value ^ byte, FNV_PRIME) >>> 0;
  return value;
}

// Point 0 is the bare name and point i is `i#node`: the number goes first, because FNV-1a mixes
// the first bytes of a text far better than its last ones.
function labelsOf(node: string, count: number): string[] {
  const labels = [node];
  for (let index = 1; index < count; index++) labels.push(`${index}#${node}`);
  return labels;
}

interface Point {
  position: number;
  label: string;
  node: string;
}

function byRingOrder(one: Point, other: Point): number {
  if (one.position !== other.position) return one.position - other.position;
  return one.label < other.label ? -1 : one.label > other.label ? 1 : 0;
}

// The index of the first point at or after the position, wrapping to 0 past the last point.
function startOf(points: Point[], position: number): number {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (points[middle].position < position) low = middle + 1;
    else high = middle;
  }
  return low < points.length ? low : 0;
}

function ownerIn(points: Point[], position: number): string {
  return points.length === 0 ? "" : points[startOf(points, position)].node;
}

function moduloIn(joined: string[], key: string): string {
  return joined.length === 0 ? "" : joined[fnv1a(key) % joined.length];
}

// The ring is a list of points sorted by position and then by label, which is the ring order
// with its tie-break. A key's owner is the first point at or after the key's position, found by
// binary search, wrapping to the first point.
export class HashRing {
  private points: Point[] = [];
  private joined: string[] = [];
  private counts = new Map<string, number>();
  private tracked = new Set<string>();
  private report: string[][] = [];

  // Level 1
  positionOf(text: string): number {
    return fnv1a(text);
  }

  addNode(node: string): number {
    return this.addVirtualNode(node, 1) ? fnv1a(node) : -1;
  }

  removeNode(node: string): boolean {
    if (!this.counts.has(node)) return false;
    const before = this.owners();
    this.points = this.points.filter((point) => point.node !== node);
    this.joined = this.joined.filter((name) => name !== node);
    this.counts.delete(node);
    this.makeReport(before);
    return true;
  }

  nodes(): string[] {
    return this.joined.slice().sort();
  }

  nodeFor(key: string): string {
    return ownerIn(this.points, fnv1a(key));
  }

  moduloNodeFor(key: string): string {
    return moduloIn(this.joined, key);
  }

  countMoves(keys: string[], node: string): number[] {
    if (this.counts.has(node)) return [];
    const grown = [...this.points, { position: fnv1a(node), label: node, node }].sort(byRingOrder);
    const joined = [...this.joined, node];
    let ringMoves = 0;
    let moduloMoves = 0;
    for (const key of keys) {
      const position = fnv1a(key);
      if (ownerIn(this.points, position) !== ownerIn(grown, position)) ringMoves++;
      if (moduloIn(this.joined, key) !== moduloIn(joined, key)) moduloMoves++;
    }
    return [ringMoves, moduloMoves];
  }

  // Level 2
  addVirtualNode(node: string, count: number): boolean {
    if (this.counts.has(node) || count < 1) return false;
    const before = this.owners();
    for (const label of labelsOf(node, count)) this.points.push({ position: fnv1a(label), label, node });
    this.points.sort(byRingOrder);
    this.joined.push(node);
    this.counts.set(node, count);
    this.makeReport(before);
    return true;
  }

  positions(node: string): number[] {
    const count = this.counts.get(node);
    return count === undefined ? [] : labelsOf(node, count).map(fnv1a);
  }

  arcShare(): number[] {
    const share = new Map<string, number>();
    this.points.forEach((point, index) => {
      const previous = this.points[(index + this.points.length - 1) % this.points.length].position;
      const arc = index > 0 ? point.position - previous : point.position - previous + RING_SIZE;
      share.set(point.node, (share.get(point.node) ?? 0) + arc);
    });
    return this.nodes().map((node) => share.get(node) ?? 0);
  }

  keyCounts(keys: string[]): number[] {
    const counts = new Map<string, number>();
    for (const key of keys) {
      const owner = this.nodeFor(key);
      counts.set(owner, (counts.get(owner) ?? 0) + 1);
    }
    return this.nodes().map((node) => counts.get(node) ?? 0);
  }

  // Level 3
  trackKeys(keys: string[]): number {
    for (const key of keys) this.tracked.add(key);
    return this.tracked.size;
  }

  lastMoves(): string[][] {
    return this.report.map((row) => row.slice());
  }

  ownedKeys(node: string): string[] {
    if (!this.counts.has(node)) return [];
    return [...this.tracked].filter((key) => this.nodeFor(key) === node).sort();
  }

  // Level 4
  replicas(key: string, count: number): string[] {
    if (count < 1 || this.points.length === 0) return [];
    const start = startOf(this.points, fnv1a(key));
    const found: string[] = [];
    for (let step = 0; step < this.points.length && found.length < count; step++) {
      const node = this.points[(start + step) % this.points.length].node;
      if (!found.includes(node)) found.push(node);
    }
    return found;
  }

  assignBounded(keys: string[], numerator: number, denominator: number): string[] {
    if (this.points.length === 0 || keys.length === 0) return [];
    const total = (denominator + numerator) * keys.length;
    const share = denominator * this.joined.length;
    const capacity = Math.floor((total + share - 1) / share);
    const load = new Map<string, number>();
    return keys.map((key) => {
      let index = startOf(this.points, fnv1a(key));
      while ((load.get(this.points[index].node) ?? 0) >= capacity) {
        index = (index + 1) % this.points.length;
      }
      const node = this.points[index].node;
      load.set(node, (load.get(node) ?? 0) + 1);
      return node;
    });
  }

  // Shared
  private owners(): Map<string, string> {
    const owners = new Map<string, string>();
    for (const key of this.tracked) owners.set(key, this.nodeFor(key));
    return owners;
  }

  private makeReport(before: Map<string, string>): void {
    const rows: string[][] = [];
    for (const [key, from] of before) {
      const to = this.nodeFor(key);
      if (from !== to) rows.push([key, from, to]);
    }
    this.report = rows.sort((one, other) => (one[0] < other[0] ? -1 : one[0] > other[0] ? 1 : 0));
  }
}
