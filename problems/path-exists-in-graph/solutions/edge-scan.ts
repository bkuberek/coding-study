export function hasPath(n: number, edges: number[][], source: number, target: number): boolean {
  const reached = new Array<boolean>(n).fill(false);
  reached[source] = true;
  let changed = true;
  while (changed && !reached[target]) {
    changed = false;
    for (const [a, b] of edges) {
      // A connection with exactly one reached end brings the other end in.
      if (reached[a] !== reached[b]) {
        reached[a] = true;
        reached[b] = true;
        changed = true;
      }
    }
  }
  return reached[target];
}
