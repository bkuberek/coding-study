export function numIslands(grid: string[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  let islands = 0;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      if (grid[row][col] !== "1") continue;
      islands++;
      // Sink each land square when it is discovered, so it is pushed at most once.
      grid[row][col] = "0";
      const stack: number[] = [row * cols + col];
      while (stack.length > 0) {
        const cell = stack.pop()!;
        const r = Math.floor(cell / cols);
        const c = cell % cols;
        for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] === "1") {
            grid[nr][nc] = "0";
            stack.push(nr * cols + nc);
          }
        }
      }
    }
  }
  return islands;
}
