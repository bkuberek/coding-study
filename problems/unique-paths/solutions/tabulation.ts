const MOD = 1_000_000_007;

export function uniquePaths(m: number, n: number): number {
  // routes[row][column] is the number of routes from the start to that cell. The first row
  // and the first column can only be reached in a straight line.
  const routes = Array.from({ length: m }, () => new Int32Array(n).fill(1));
  for (let row = 1; row < m; row++) {
    for (let column = 1; column < n; column++) {
      routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) % MOD;
    }
  }
  return routes[m - 1][n - 1];
}
