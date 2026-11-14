const FRESH = 1;
const ROTTEN = 2;

export function orangesRotting(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  let frontier: [number, number][] = [];
  let fresh = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (grid[r][c] === ROTTEN) frontier.push([r, c]);
      else if (grid[r][c] === FRESH) fresh++;
    }
  }
  let minutes = 0;
  // Each round rots every fresh neighbor of the current frontier: one minute.
  while (frontier.length > 0 && fresh > 0) {
    minutes++;
    const next: [number, number][] = [];
    for (const [r, c] of frontier) {
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] === FRESH) {
          grid[nr][nc] = ROTTEN;
          fresh--;
          next.push([nr, nc]);
        }
      }
    }
    frontier = next;
  }
  return fresh === 0 ? minutes : -1;
}
