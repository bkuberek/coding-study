class DisjointSets {
  private readonly parent: number[];
  private readonly size: number[]; // size[r]: number of nodes in the tree rooted at r

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

  // Merges the sets of a and b; false when they were already one set.
  union(a: number, b: number): boolean {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) {
      return false;
    }
    if (this.size[rootA] < this.size[rootB]) {
      [rootA, rootB] = [rootB, rootA];
    }
    this.parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
    this.size[rootA] += this.size[rootB];
    return true;
  }
}

export function countComponents(n: number, edges: number[][]): number {
  const sets = new DisjointSets(n);
  let components = n;
  for (const [a, b] of edges) {
    if (sets.union(a, b)) {
      components--;
    }
  }
  return components;
}
