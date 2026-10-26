export function maximalSquare(matrix: string[][]): number {
  const columns = matrix[0].length;
  // side[c + 1] is the largest square ending at column c of the current row (before the
  // update: of the row above); side[0] is a border of zeros.
  const side = new Int16Array(columns + 1);
  let best = 0;
  for (const row of matrix) {
    let diagonal = 0; // the row-above value of the previous column, saved before it is overwritten
    for (let c = 1; c <= columns; c++) {
      const above = side[c];
      side[c] = row[c - 1] === "1" ? 1 + Math.min(above, side[c - 1], diagonal) : 0;
      best = Math.max(best, side[c]);
      diagonal = above;
    }
  }
  return best * best;
}
