export function findRedundantConnection(edges: number[][]): number[] {
  const neighbors: number[][] = Array.from({ length: edges.length + 1 }, () => []);
  const connected = (start: number, goal: number): boolean => {
    const seen = new Set<number>([start]);
    const stack = [start];
    while (stack.length > 0) {
      const node = stack.pop() as number;
      if (node === goal) {
        return true;
      }
      for (const neighbor of neighbors[node]) {
        if (!seen.has(neighbor)) {
          seen.add(neighbor);
          stack.push(neighbor);
        }
      }
    }
    return false;
  };
  for (const [a, b] of edges) {
    // The first edge whose ends are already connected closes the only cycle.
    if (connected(a, b)) {
      return [a, b];
    }
    neighbors[a].push(b);
    neighbors[b].push(a);
  }
  return [];
}
