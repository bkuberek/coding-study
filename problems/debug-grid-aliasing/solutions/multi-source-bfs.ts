const STEPS = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function burnTimes(grid: number[][]): number[][] {
  const rows = grid.length;
  const cols = grid[0].length;
  const times: number[][] = Array.from({ length: rows }, () => new Array<number>(cols).fill(-1));
  const queue: [number, number][] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (grid[r][c] === 2) {
        times[r][c] = 0;
        queue.push([r, c]);
      }
    }
  }
  // A read index instead of Array.shift(), which is O(n) per call.
  for (let head = 0; head < queue.length; head++) {
    const [r, c] = queue[head];
    for (const [dr, dc] of STEPS) {
      const nr = r + dr;
      const nc = c + dc;
      if (
        nr >= 0 &&
        nr < rows &&
        nc >= 0 &&
        nc < cols &&
        grid[nr][nc] === 1 &&
        times[nr][nc] === -1
      ) {
        times[nr][nc] = times[r][c] + 1;
        queue.push([nr, nc]);
      }
    }
  }
  return times;
}
