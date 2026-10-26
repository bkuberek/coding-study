class DisjointSet {
  private readonly parent: Int32Array;
  private readonly size: Int32Array;

  constructor(count: number) {
    this.parent = Int32Array.from({ length: count }, (_, i) => i);
    this.size = new Int32Array(count).fill(1);
  }

  find(node: number): number {
    let root = node;
    while (this.parent[root] !== root) root = this.parent[root];
    while (this.parent[node] !== root) {
      const next = this.parent[node];
      this.parent[node] = root;
      node = next;
    }
    return root;
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

export function isBipartite(graph: number[][]): boolean {
  const teams = new DisjointSet(graph.length);
  // All neighbors of a node must share a team, so they go into one group.
  for (const neighbors of graph) {
    for (const neighbor of neighbors) teams.union(neighbors[0], neighbor);
  }
  // A split exists exactly when no edge has both ends in one group.
  return graph.every((neighbors, node) => neighbors.every((neighbor) => teams.find(node) !== teams.find(neighbor)));
}
