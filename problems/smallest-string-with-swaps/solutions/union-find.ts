class DisjointSets {
  private readonly parent: number[];
  private readonly size: number[]; // size[r]: number of positions in the tree rooted at r

  constructor(count: number) {
    this.parent = Array.from({ length: count }, (_, x) => x);
    this.size = new Array<number>(count).fill(1);
  }

  find(x: number): number {
    let root = x;
    while (this.parent[root] !== root) {
      root = this.parent[root];
    }
    while (this.parent[x] !== root) {
      // Path compression: point every node on the path at the root.
      const next = this.parent[x];
      this.parent[x] = root;
      x = next;
    }
    return root;
  }

  union(a: number, b: number): void {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) {
      return;
    }
    if (this.size[rootA] < this.size[rootB]) {
      [rootA, rootB] = [rootB, rootA];
    }
    this.parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
    this.size[rootA] += this.size[rootB];
  }
}

export function smallestStringWithSwaps(s: string, pairs: number[][]): string {
  const sets = new DisjointSets(s.length);
  for (const [a, b] of pairs) {
    sets.union(a, b);
  }
  // Positions are added in increasing order, so each group's list is sorted.
  const groups = new Map<number, number[]>();
  for (let position = 0; position < s.length; position++) {
    const root = sets.find(position);
    const group = groups.get(root);
    if (group === undefined) {
      groups.set(root, [position]);
    } else {
      group.push(position);
    }
  }
  const letters = [...s];
  for (const positions of groups.values()) {
    const sorted = positions.map((position) => s[position]).sort();
    positions.forEach((position, k) => {
      letters[position] = sorted[k];
    });
  }
  return letters.join("");
}
