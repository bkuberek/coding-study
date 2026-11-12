// A B+ tree: every entry lives in a leaf, the leaves are linked left to right, and the inner nodes
// hold separator keys that only steer the way down. Keys are number arrays compared field by
// field. Every change walks down once and keeps the path, then repairs nodes on the way back up:
// splits after an insert, borrows and merges after a remove.

class Page {
  leaf: boolean;
  keys: number[][] = [];
  rows: number[] = [];
  children: Page[] = [];
  next: Page | null = null;

  constructor(leaf: boolean) {
    this.leaf = leaf;
  }
}

type Step = { parent: Page; index: number };

function compareKeys(first: number[], second: number[]): number {
  const shared = Math.min(first.length, second.length);
  for (let i = 0; i < shared; i++) {
    if (first[i] !== second[i]) return first[i] < second[i] ? -1 : 1;
  }
  return first.length - second.length;
}

// The first position whose key is at least `key` (orEqual false), or the number of keys that are
// at most `key` (orEqual true).
function bound(keys: number[][], key: number[], orEqual: boolean): number {
  let low = 0;
  let high = keys.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    const order = compareKeys(keys[middle], key);
    if (order < 0 || (orEqual && order === 0)) low = middle + 1;
    else high = middle;
  }
  return low;
}

function sizes(total: number, per: number, minimum: number, maximum: number): number[] {
  const result: number[] = Array(Math.floor(total / per)).fill(per);
  if (total % per !== 0) result.push(total % per);
  if (result.length > 1 && result[result.length - 1] < minimum) {
    const pool = (result.pop() as number) + (result.pop() as number);
    if (pool <= maximum) result.push(pool);
    else result.push(Math.ceil(pool / 2), Math.floor(pool / 2));
  }
  return result;
}

export class BTreeIndex {
  private d: number;
  private root = new Page(true);

  constructor(minKeys: number) {
    this.d = minKeys;
  }

  // Level 1
  search(key: number[]): number {
    const [leaf] = this.descend(key);
    const at = bound(leaf.keys, key, false);
    return this.holds(leaf, at, key) ? leaf.rows[at] : -1;
  }

  insert(key: number[], rowId: number): boolean {
    const [leaf, path] = this.descend(key);
    const at = bound(leaf.keys, key, false);
    if (this.holds(leaf, at, key)) return false;
    leaf.keys.splice(at, 0, [...key]);
    leaf.rows.splice(at, 0, rowId);
    this.splitUpward(leaf, path);
    return true;
  }

  levels(): string[] {
    const lines: string[] = [];
    let level = [this.root];
    while (level.length > 0) {
      lines.push(level.map((node) => `[${node.keys.map((key) => key.join(",")).join(" ")}]`).join(" "));
      level = level.flatMap((node) => node.children);
    }
    return lines;
  }

  // Level 2
  rangeScan(low: number[], high: number[]): number[] {
    return this.scan(low, high)[0];
  }

  scanVisits(low: number[], high: number[]): number {
    return this.scan(low, high)[1];
  }

  height(): number {
    let count = 1;
    for (let node = this.root; !node.leaf; node = node.children[0]) count++;
    return count;
  }

  // Level 3
  remove(key: number[]): boolean {
    const [leaf, path] = this.descend(key);
    const at = bound(leaf.keys, key, false);
    if (!this.holds(leaf, at, key)) return false;
    leaf.keys.splice(at, 1);
    leaf.rows.splice(at, 1);
    let current = leaf;
    while (path.length > 0 && current.keys.length < this.d) {
      const { parent, index } = path.pop() as Step;
      if (current.leaf) this.fixLeaf(parent, index);
      else this.fixInner(parent, index);
      current = parent;
    }
    if (!this.root.leaf && this.root.keys.length === 0) this.root = this.root.children[0];
    return true;
  }

  // Level 4
  bulkLoad(keys: number[][], rowIds: number[], fillPercent: number): boolean {
    if (!this.root.leaf || this.root.keys.length > 0) return false;
    for (let i = 0; i + 1 < keys.length; i++) {
      if (compareKeys(keys[i], keys[i + 1]) >= 0) return false;
    }
    if (keys.length === 0) return true;
    const d = this.d;
    const per = Math.floor((2 * d * fillPercent) / 100);
    let level: Page[] = [];
    let lowest: number[][] = [];
    let start = 0;
    for (const size of sizes(keys.length, per, d, 2 * d)) {
      const leaf = new Page(true);
      leaf.keys = keys.slice(start, start + size).map((key) => [...key]);
      leaf.rows = rowIds.slice(start, start + size);
      if (level.length > 0) level[level.length - 1].next = leaf;
      level.push(leaf);
      lowest.push(leaf.keys[0]);
      start += size;
    }
    while (level.length > 1) {
      const parents: Page[] = [];
      const parentLowest: number[][] = [];
      start = 0;
      for (const size of sizes(level.length, per + 1, d + 1, 2 * d + 1)) {
        const parent = new Page(false);
        parent.children = level.slice(start, start + size);
        parent.keys = lowest.slice(start + 1, start + size);
        parents.push(parent);
        parentLowest.push(lowest[start]);
        start += size;
      }
      level = parents;
      lowest = parentLowest;
    }
    this.root = level[0];
    return true;
  }

  prefixScan(prefix: number[]): number[] {
    const width = prefix.length;
    let node = this.root;
    while (!node.leaf) {
      const index = node.keys.filter((separator) => compareKeys(separator.slice(0, width), prefix) < 0).length;
      node = node.children[index];
    }
    const rows: number[] = [];
    for (let leaf: Page | null = node; leaf !== null; leaf = leaf.next) {
      for (let i = 0; i < leaf.keys.length; i++) {
        const order = compareKeys(leaf.keys[i].slice(0, width), prefix);
        if (order > 0) return rows;
        if (order === 0) rows.push(leaf.rows[i]);
      }
    }
    return rows;
  }

  // Helpers
  private descend(key: number[]): [Page, Step[]] {
    const path: Step[] = [];
    let node = this.root;
    while (!node.leaf) {
      const index = bound(node.keys, key, true);
      path.push({ parent: node, index });
      node = node.children[index];
    }
    return [node, path];
  }

  private holds(leaf: Page, at: number, key: number[]): boolean {
    return at < leaf.keys.length && compareKeys(leaf.keys[at], key) === 0;
  }

  private splitUpward(leaf: Page, path: Step[]): void {
    const d = this.d;
    if (leaf.keys.length <= 2 * d) return;
    const right = new Page(true);
    right.keys = leaf.keys.splice(d);
    right.rows = leaf.rows.splice(d);
    right.next = leaf.next;
    leaf.next = right;
    let left = leaf;
    let separator = right.keys[0];
    let created = right;
    while (path.length > 0) {
      const { parent, index } = path.pop() as Step;
      parent.keys.splice(index, 0, separator);
      parent.children.splice(index + 1, 0, created);
      if (parent.keys.length <= 2 * d) return;
      const sibling = new Page(false);
      sibling.keys = parent.keys.splice(d + 1);
      sibling.children = parent.children.splice(d + 1);
      separator = parent.keys.pop() as number[];
      created = sibling;
      left = parent;
    }
    const top = new Page(false);
    top.keys = [separator];
    top.children = [left, created];
    this.root = top;
  }

  private scan(low: number[], high: number[]): [number[], number] {
    const [first, path] = this.descend(low);
    let leaf = first;
    let visits = path.length + 1;
    const rows: number[] = [];
    let at = bound(leaf.keys, low, false);
    for (;;) {
      for (; at < leaf.keys.length; at++) {
        if (compareKeys(leaf.keys[at], high) > 0) return [rows, visits];
        rows.push(leaf.rows[at]);
      }
      if (leaf.next === null) return [rows, visits];
      leaf = leaf.next;
      at = 0;
      visits++;
    }
  }

  private fixLeaf(parent: Page, index: number): void {
    const node = parent.children[index];
    const left = index > 0 ? parent.children[index - 1] : null;
    const right = index + 1 < parent.children.length ? parent.children[index + 1] : null;
    if (left !== null && left.keys.length > this.d) {
      node.keys.unshift(left.keys.pop() as number[]);
      node.rows.unshift(left.rows.pop() as number);
      parent.keys[index - 1] = node.keys[0];
    } else if (right !== null && right.keys.length > this.d) {
      node.keys.push(right.keys.shift() as number[]);
      node.rows.push(right.rows.shift() as number);
      parent.keys[index] = right.keys[0];
    } else if (left !== null) {
      left.keys.push(...node.keys);
      left.rows.push(...node.rows);
      left.next = node.next;
      parent.keys.splice(index - 1, 1);
      parent.children.splice(index, 1);
    } else {
      const sibling = right as Page;
      node.keys.push(...sibling.keys);
      node.rows.push(...sibling.rows);
      node.next = sibling.next;
      parent.keys.splice(index, 1);
      parent.children.splice(index + 1, 1);
    }
  }

  private fixInner(parent: Page, index: number): void {
    const node = parent.children[index];
    const left = index > 0 ? parent.children[index - 1] : null;
    const right = index + 1 < parent.children.length ? parent.children[index + 1] : null;
    if (left !== null && left.keys.length > this.d) {
      node.keys.unshift(parent.keys[index - 1]);
      parent.keys[index - 1] = left.keys.pop() as number[];
      node.children.unshift(left.children.pop() as Page);
    } else if (right !== null && right.keys.length > this.d) {
      node.keys.push(parent.keys[index]);
      parent.keys[index] = right.keys.shift() as number[];
      node.children.push(right.children.shift() as Page);
    } else if (left !== null) {
      left.keys.push(parent.keys[index - 1], ...node.keys);
      left.children.push(...node.children);
      parent.keys.splice(index - 1, 1);
      parent.children.splice(index, 1);
    } else {
      const sibling = right as Page;
      node.keys.push(parent.keys[index], ...sibling.keys);
      node.children.push(...sibling.children);
      parent.keys.splice(index, 1);
      parent.children.splice(index + 1, 1);
    }
  }
}
