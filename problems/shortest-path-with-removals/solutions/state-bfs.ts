export function shortestPath(grid: number[][], k: number): number {
  const rows = grid.length;
  const cols = grid[0].length;
  // A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
  // removals than that never help.
  const budget = Math.min(k, Math.max(0, rows + cols - 3));
  const layers = budget + 1;
  // State (r, c, used) is encoded as (r * cols + c) * layers + used.
  const seen = new Uint8Array(rows * cols * layers);
  seen[0] = 1;
  let level = [0];
  for (let moves = 0; level.length > 0; moves++) {
    const next: number[] = [];
    for (const state of level) {
      const used = state % layers;
      const cell = (state - used) / layers;
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      if (r === rows - 1 && c === cols - 1) return moves;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const after = used + grid[nr][nc];
        const following = (nr * cols + nc) * layers + after;
        if (after <= budget && seen[following] === 0) {
          seen[following] = 1;
          next.push(following);
        }
      }
    }
    level = next;
  }
  return -1;
}
