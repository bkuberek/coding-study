const UNCOLORED = -1;

export function isBipartite(graph: number[][]): boolean {
  const color = new Int8Array(graph.length).fill(UNCOLORED);
  // Every piece of the graph needs its own start node.
  for (let start = 0; start < graph.length; start++) {
    if (color[start] !== UNCOLORED) continue;
    color[start] = 0;
    const queue = [start];
    for (let head = 0; head < queue.length; head++) {
      const node = queue[head];
      for (const neighbor of graph[node]) {
        if (color[neighbor] === UNCOLORED) {
          color[neighbor] = 1 - color[node];
          queue.push(neighbor);
        } else if (color[neighbor] === color[node]) {
          return false;
        }
      }
    }
  }
  return true;
}
