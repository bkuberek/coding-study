const STEPS = [-1, 0, 1].flatMap((dr) => [-1, 0, 1].map((dc) => [dr, dc])).filter(([dr, dc]) => dr !== 0 || dc !== 0);

export function shortestPathBinaryMatrix(grid: number[][]): number {
  const n = grid.length;
  if (grid[0][0] === 1 || grid[n - 1][n - 1] === 1) return -1;
  const unreached = n * n + 1;
  const dist = Array.from({ length: n }, () => new Array<number>(n).fill(unreached));
  dist[0][0] = 1;
  let forward = true;
  let changed = true;
  while (changed) {
    changed = false;
    // Each sweep lets every open cell take the best distance offered by a neighbor;
    // alternating the scan direction lets improvements travel both ways quickly.
    for (let i = 0; i < n * n; i++) {
      const cell = forward ? i : n * n - 1 - i;
      const r = Math.floor(cell / n);
      const c = cell % n;
      if (grid[r][c] === 1) continue;
      for (const [dr, dc] of STEPS) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < n && nc >= 0 && nc < n && dist[nr][nc] + 1 < dist[r][c]) {
          dist[r][c] = dist[nr][nc] + 1;
          changed = true;
        }
      }
    }
    forward = !forward;
  }
  return dist[n - 1][n - 1] < unreached ? dist[n - 1][n - 1] : -1;
}
