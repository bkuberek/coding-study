export function criticalConnections(n: number, connections: number[][]): number[][] {
  const adjacency: number[][] = Array.from({ length: n }, () => []);
  for (const [a, b] of connections) {
    adjacency[a].push(b);
    adjacency[b].push(a);
  }
  // discovered[v] is the order in which v was first reached (-1: not yet).
  // low[v] is the earliest discovery time reachable from v's subtree using at most one
  // cable that is not a tree edge.
  const discovered = new Int32Array(n).fill(-1);
  const low = new Int32Array(n);
  const bridges: number[][] = [];
  let clock = 0;

  const visit = (server: number, parent: number): void => {
    discovered[server] = low[server] = clock++;
    for (const neighbor of adjacency[server]) {
      if (neighbor === parent) continue; // the tree edge we arrived by is not a way back
      if (discovered[neighbor] === -1) {
        visit(neighbor, server);
        low[server] = Math.min(low[server], low[neighbor]);
        if (low[neighbor] > discovered[server]) bridges.push([server, neighbor]);
      } else {
        low[server] = Math.min(low[server], discovered[neighbor]);
      }
    }
  };

  visit(0, -1);
  return bridges;
}
