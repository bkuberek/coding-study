export function floodFill(grid: number[][], row: number, col: number, newColor: number): number[][] {
  const oldColor = grid[row][col];
  if (oldColor === newColor) return grid;

  const paint = (r: number, c: number): void => {
    if (r < 0 || r >= grid.length || c < 0 || c >= grid[0].length || grid[r][c] !== oldColor) {
      return;
    }
    grid[r][c] = newColor;
    paint(r + 1, c);
    paint(r - 1, c);
    paint(r, c + 1);
    paint(r, c - 1);
  };

  paint(row, col);
  return grid;
}
