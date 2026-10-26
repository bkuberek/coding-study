const MOD = 1_000_000_007;

export function uniquePaths(m: number, n: number): number {
  // Transposing the grid does not change the count, so keep the row along the shorter side.
  const width = Math.min(m, n);
  const height = Math.max(m, n);
  // Before the update, routes[column] belongs to the row above; after it, to the current row.
  const routes = new Int32Array(width).fill(1);
  for (let row = 1; row < height; row++) {
    for (let column = 1; column < width; column++) {
      routes[column] = (routes[column] + routes[column - 1]) % MOD;
    }
  }
  return routes[width - 1];
}
