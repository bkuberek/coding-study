export function maxAreaOfIsland(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const seen = new Uint8Array(rows * cols);
  let best = 0;
  for (let start = 0; start < rows * cols; start++) {
    if (grid[Math.floor(start / cols)][start % cols] !== 1 || seen[start] === 1) continue;
    seen[start] = 1;
    const stack = [start];
    let area = 0;
    while (stack.length > 0) {
      const cell = stack.pop()!;
      area++;
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const next = nr * cols + nc;
        if (grid[nr][nc] === 1 && seen[next] === 0) {
          seen[next] = 1;
          stack.push(next);
        }
      }
    }
    best = Math.max(best, area);
  }
  return best;
}
