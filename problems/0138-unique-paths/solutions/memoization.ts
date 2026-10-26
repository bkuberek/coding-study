const MOD = 1_000_000_007;

export function uniquePaths(m: number, n: number): number {
  // routes[row][column] caches the number of routes from that cell to the goal; -1 is unknown.
  const routes = Array.from({ length: m }, () => new Int32Array(n).fill(-1));
  const count = (row: number, column: number): number => {
    if (row === m - 1 || column === n - 1) {
      return 1;
    }
    if (routes[row][column] < 0) {
      routes[row][column] = (count(row + 1, column) + count(row, column + 1)) % MOD;
    }
    return routes[row][column];
  };
  return count(0, 0);
}
