export function countComponents(n: number, edges: number[][]): number {
  const parent = Array.from({ length: n }, (_, x) => x); // parent[x] === x marks a root
  const find = (x: number): number => {
    while (parent[x] !== x) {
      x = parent[x];
    }
    return x;
  };
  let components = n;
  for (const [a, b] of edges) {
    const rootA = find(a);
    const rootB = find(b);
    if (rootA !== rootB) {
      parent[rootA] = rootB; // no balancing: trees can grow into long chains
      components--;
    }
  }
  return components;
}
