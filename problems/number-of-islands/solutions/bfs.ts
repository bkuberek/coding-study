export function numIslands(grid: string[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const visited = new Uint8Array(rows * cols);
  const queue = new Int32Array(rows * cols);
  let islands = 0;
  for (let start = 0; start < rows * cols; start++) {
    if (grid[Math.floor(start / cols)][start % cols] !== "1" || visited[start] === 1) continue;
    islands++;
    visited[start] = 1;
    // Every cell enters the queue at most once, so one preallocated buffer serves all islands.
    let head = 0;
    let tail = 0;
    queue[tail++] = start;
    while (head < tail) {
      const cell = queue[head++];
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const next = nr * cols + nc;
        if (grid[nr][nc] === "1" && visited[next] === 0) {
          visited[next] = 1;
          queue[tail++] = next;
        }
      }
    }
  }
  return islands;
}
