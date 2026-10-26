// Debug: Grid Aliasing. Some tests fail: find the bug and fix it.
const STEPS = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function burnTimes(grid: number[][]): number[][] {
  const rows = grid.length;
  const cols = grid[0].length;
  const times: number[][] = new Array(rows).fill(new Array(cols).fill(-1));
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (grid[r][c] === 2) {
        times[r][c] = 0;
      }
    }
  }

  let current = grid;
  let minute = 0;
  let spreading = true;
  while (spreading) {
    minute++;
    spreading = false;
    const upcoming = [...current];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (current[r][c] !== 2) {
          continue;
        }
        for (const [dr, dc] of STEPS) {
          const nr = r + dr;
          const nc = c + dc;
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && current[nr][nc] === 1) {
            upcoming[nr][nc] = 2;
            times[nr][nc] = minute;
            spreading = true;
          }
        }
      }
    }
    current = upcoming;
  }
  return times;
}
