export function findRedundantConnection(edges: number[][]): number[] {
  const parent = Array.from({ length: edges.length + 1 }, (_, x) => x); // parent[x] === x marks a root
  const find = (x: number): number => {
    while (parent[x] !== x) {
      x = parent[x];
    }
    return x;
  };
  for (const [a, b] of edges) {
    const rootA = find(a);
    const rootB = find(b);
    if (rootA === rootB) {
      return [a, b]; // the ends are already connected: this edge closes the cycle
    }
    parent[rootA] = rootB; // no balancing: trees can grow into long chains
  }
  return [];
}
