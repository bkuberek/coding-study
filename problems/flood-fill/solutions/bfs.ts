export function floodFill(grid: number[][], row: number, col: number, newColor: number): number[][] {
  const oldColor = grid[row][col];
  if (oldColor === newColor) return grid;
  const rows = grid.length;
  const cols = grid[0].length;
  // Every square is queued at most once, so a typed array of that size is a complete queue:
  // `head` walks forward and `tail` marks the end.
  const queue = new Int32Array(rows * cols);
  let head = 0;
  let tail = 0;
  grid[row][col] = newColor;
  queue[tail++] = row * cols + col;
  while (head < tail) {
    const cell = queue[head++];
    const r = Math.floor(cell / cols);
    const c = cell % cols;
    for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] === oldColor) {
        grid[nr][nc] = newColor;
        queue[tail++] = nr * cols + nc;
      }
    }
  }
  return grid;
}
