export function hasPath(n: number, edges: number[][], source: number, target: number): boolean {
  // neighbors[node] lists every node joined to `node`; each connection works both ways.
  const neighbors: number[][] = Array.from({ length: n }, () => []);
  for (const [a, b] of edges) {
    neighbors[a].push(b);
    neighbors[b].push(a);
  }
  const seen = new Array<boolean>(n).fill(false);
  seen[source] = true;
  // Each node is queued at most once, so an array of n slots and a moving head make a queue.
  const queue: number[] = [source];
  for (let head = 0; head < queue.length; head++) {
    const node = queue[head];
    if (node === target) return true;
    for (const neighbor of neighbors[node]) {
      if (!seen[neighbor]) {
        seen[neighbor] = true;
        queue.push(neighbor);
      }
    }
  }
  return false;
}
