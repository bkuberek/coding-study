const STEPS = [-1, 0, 1].flatMap((dr) => [-1, 0, 1].map((dc) => [dr, dc])).filter(([dr, dc]) => dr !== 0 || dc !== 0);

export function shortestPathBinaryMatrix(grid: number[][]): number {
  const n = grid.length;
  if (grid[0][0] === 1 || grid[n - 1][n - 1] === 1) return -1;
  // dist 0 means "not reached yet": every reached cell has a length of at least 1.
  const dist = new Int32Array(n * n);
  dist[0] = 1;
  const queue = [0];
  for (let head = 0; head < queue.length; head++) {
    const cell = queue[head];
    if (cell === n * n - 1) return dist[cell];
    const r = Math.floor(cell / n);
    const c = cell % n;
    for (const [dr, dc] of STEPS) {
      const nr = r + dr;
      const nc = c + dc;
      if (nr < 0 || nr >= n || nc < 0 || nc >= n || grid[nr][nc] === 1) continue;
      const next = nr * n + nc;
      if (dist[next] === 0) {
        dist[next] = dist[cell] + 1;
        queue.push(next);
      }
    }
  }
  return -1;
}
