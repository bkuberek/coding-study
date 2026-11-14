export function maximalSquare(matrix: string[][]): number {
  const rows = matrix.length;
  const columns = matrix[0].length;
  // side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
  // -1 is unknown.
  const side = Array.from({ length: rows }, () => new Int16Array(columns).fill(-1));
  const largest = (r: number, c: number): number => {
    if (r === rows || c === columns || matrix[r][c] === "0") {
      return 0;
    }
    if (side[r][c] < 0) {
      side[r][c] = 1 + Math.min(largest(r + 1, c), largest(r, c + 1), largest(r + 1, c + 1));
    }
    return side[r][c];
  };
  let best = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      best = Math.max(best, largest(r, c));
    }
  }
  return best * best;
}
