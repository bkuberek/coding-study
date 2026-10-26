const FRESH = 1;
const ROTTEN = 2;

export function orangesRotting(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const touchesRot = (r: number, c: number): boolean =>
    (r > 0 && grid[r - 1][c] === ROTTEN) ||
    (r + 1 < rows && grid[r + 1][c] === ROTTEN) ||
    (c > 0 && grid[r][c - 1] === ROTTEN) ||
    (c + 1 < cols && grid[r][c + 1] === ROTTEN);

  let minutes = 0;
  for (;;) {
    // Collect this minute's changes before applying any, so new rot waits a minute.
    const turning: [number, number][] = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (grid[r][c] === FRESH && touchesRot(r, c)) turning.push([r, c]);
      }
    }
    if (turning.length === 0) break;
    for (const [r, c] of turning) grid[r][c] = ROTTEN;
    minutes++;
  }
  return grid.some((row) => row.includes(FRESH)) ? -1 : minutes;
}
