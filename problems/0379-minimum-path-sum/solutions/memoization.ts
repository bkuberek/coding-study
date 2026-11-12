export function minPathSum(grid: number[][]): number {
  const rows = grid.length;
  const columns = grid[0].length;
  const unknown = -1;
  const cheapest: number[][] = Array.from({ length: rows }, () => new Array<number>(columns).fill(unknown));

  function cheapestTo(row: number, column: number): number {
    if (cheapest[row][column] !== unknown) {
      return cheapest[row][column];
    }
    let arrival: number;
    if (row === 0 && column === 0) {
      arrival = 0;
    } else if (row === 0) {
      arrival = cheapestTo(row, column - 1);
    } else if (column === 0) {
      arrival = cheapestTo(row - 1, column);
    } else {
      arrival = Math.min(cheapestTo(row - 1, column), cheapestTo(row, column - 1));
    }
    cheapest[row][column] = arrival + grid[row][column];
    return cheapest[row][column];
  }

  return cheapestTo(rows - 1, columns - 1);
}
