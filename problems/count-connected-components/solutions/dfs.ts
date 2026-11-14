export function countComponents(n: number, edges: number[][]): number {
  const neighbors: number[][] = Array.from({ length: n }, () => []);
  for (const [a, b] of edges) {
    neighbors[a].push(b);
    neighbors[b].push(a);
  }
  const seen = new Array<boolean>(n).fill(false);
  let components = 0;
  for (let start = 0; start < n; start++) {
    if (seen[start]) {
      continue;
    }
    components++;
    seen[start] = true;
    const stack = [start]; // an explicit stack avoids deep recursion on long paths
    while (stack.length > 0) {
      const node = stack.pop() as number;
      for (const neighbor of neighbors[node]) {
        if (!seen[neighbor]) {
          seen[neighbor] = true;
          stack.push(neighbor);
        }
      }
    }
  }
  return components;
}
