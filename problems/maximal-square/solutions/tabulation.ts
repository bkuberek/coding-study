export function maximalSquare(matrix: string[][]): number {
  const rows = matrix.length;
  const columns = matrix[0].length;
  // side[r + 1][c + 1] is the largest all-ones square with its bottom-right corner at (r, c);
  // row 0 and column 0 are a border of zeros.
  const side = Array.from({ length: rows + 1 }, () => new Int16Array(columns + 1));
  let best = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      if (matrix[r][c] === "1") {
        side[r + 1][c + 1] = 1 + Math.min(side[r][c + 1], side[r + 1][c], side[r][c]);
        best = Math.max(best, side[r + 1][c + 1]);
      }
    }
  }
  return best * best;
}
