export function minimumObstacles(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const goal = rows * cols - 1;
  const removals = new Int32Array(rows * cols).fill(rows * cols);
  removals[0] = 0;
  // Two lists stand in for the deque: `level` holds cells at the current cost and grows with
  // zero-cost steps, `next` collects one-cost steps for the following round.
  let level = [0];
  for (let cost = 0; ; cost++) {
    const next: number[] = [];
    for (let i = 0; i < level.length; i++) {
      const cell = level[i];
      if (removals[cell] !== cost) continue; // reached again later at a lower cost
      if (cell === goal) return cost;
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const neighbor = nr * cols + nc;
        const offered = cost + grid[nr][nc];
        if (offered < removals[neighbor]) {
          removals[neighbor] = offered;
          (grid[nr][nc] === 0 ? level : next).push(neighbor);
        }
      }
    }
    level = next;
  }
}
