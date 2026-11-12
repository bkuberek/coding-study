export function minPathSum(grid: number[][]): number {
  const rows = grid.length;
  const columns = grid[0].length;
  // cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
  const cheapest: number[][] = Array.from({ length: rows }, () => new Array<number>(columns).fill(0));
  for (let row = 0; row < rows; row++) {
    for (let column = 0; column < columns; column++) {
      let arrival: number;
      if (row === 0 && column === 0) {
        arrival = 0;
      } else if (row === 0) {
        arrival = cheapest[row][column - 1];
      } else if (column === 0) {
        arrival = cheapest[row - 1][column];
      } else {
        arrival = Math.min(cheapest[row - 1][column], cheapest[row][column - 1]);
      }
      cheapest[row][column] = arrival + grid[row][column];
    }
  }
  return cheapest[rows - 1][columns - 1];
}
