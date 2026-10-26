export function swimInWater(grid: number[][]): number {
  const n = grid.length;

  // Can the goal be reached when the water stands at `time`?
  const reachable = (time: number): boolean => {
    if (grid[0][0] > time) return false;
    const seen = new Uint8Array(n * n);
    seen[0] = 1;
    const queue = [0];
    for (let head = 0; head < queue.length; head++) {
      const cell = queue[head];
      if (cell === n * n - 1) return true;
      const r = Math.floor(cell / n);
      const c = cell % n;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= n || nc < 0 || nc >= n) continue;
        const next = nr * n + nc;
        if (seen[next] === 0 && grid[nr][nc] <= time) {
          seen[next] = 1;
          queue.push(next);
        }
      }
    }
    return false;
  };

  // The answer is at least both corner heights and at most the highest floor.
  let low = Math.max(grid[0][0], grid[n - 1][n - 1]);
  let high = n * n - 1;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (reachable(middle)) high = middle;
    else low = middle + 1;
  }
  return low;
}
