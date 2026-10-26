export function shortestPath(grid: number[][], k: number): number {
  const rows = grid.length;
  const cols = grid[0].length;
  // Enough removals for the straight Manhattan route: nothing can beat it.
  if (k >= rows + cols - 3) return rows + cols - 2;
  // best[cell] is the most removals left with which the cell was reached so far.
  const best = new Int32Array(rows * cols).fill(-1);
  best[0] = k;
  let level: [number, number][] = [[0, k]];
  for (let moves = 0; level.length > 0; moves++) {
    const next: [number, number][] = [];
    for (const [cell, left] of level) {
      if (cell === rows * cols - 1) return moves;
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const following = nr * cols + nc;
        const remaining = left - grid[nr][nc];
        // A visit that arrives later with no more removals left can never do better.
        if (remaining > best[following]) {
          best[following] = remaining;
          next.push([following, remaining]);
        }
      }
    }
    level = next;
  }
  return -1;
}
