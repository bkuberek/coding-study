class DisjointSet {
  private readonly parent: Int32Array;
  private readonly size: Int32Array;

  constructor(count: number) {
    this.parent = Int32Array.from({ length: count }, (_, index) => index);
    this.size = new Int32Array(count).fill(1);
  }

  find(node: number): number {
    // Path halving: point every other node on the way up at its grandparent.
    while (this.parent[node] !== node) {
      this.parent[node] = this.parent[this.parent[node]];
      node = this.parent[node];
    }
    return node;
  }

  union(a: number, b: number): void {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) return;
    if (this.size[rootA] < this.size[rootB]) [rootA, rootB] = [rootB, rootA];
    this.parent[rootB] = rootA;
    this.size[rootA] += this.size[rootB];
  }
}

export function hasPath(n: number, edges: number[][], source: number, target: number): boolean {
  const sets = new DisjointSet(n);
  for (const [a, b] of edges) sets.union(a, b);
  return sets.find(source) === sets.find(target);
}
