export function criticalConnections(n: number, connections: number[][]): number[][] {
  const adjacency: [number, number][][] = Array.from({ length: n }, () => []);
  connections.forEach(([a, b], index) => {
    adjacency[a].push([b, index]);
    adjacency[b].push([a, index]);
  });

  // Can every server still be reached from server 0 when cable `skipped` is cut?
  const connectedWithout = (skipped: number): boolean => {
    const seen = new Uint8Array(n);
    seen[0] = 1;
    const stack = [0];
    let reached = 1;
    while (stack.length > 0) {
      for (const [neighbor, index] of adjacency[stack.pop()!]) {
        if (index !== skipped && seen[neighbor] === 0) {
          seen[neighbor] = 1;
          reached++;
          stack.push(neighbor);
        }
      }
    }
    return reached === n;
  };

  return connections.filter((_, index) => !connectedWithout(index)).map(([a, b]) => [a, b]);
}
