export function rotate(matrix: number[][]): void {
  const n = matrix.length;
  // Reflect across the main diagonal, then mirror every row left to right.
  for (let r = 0; r < n; r++) {
    for (let c = r + 1; c < n; c++) {
      const value = matrix[r][c];
      matrix[r][c] = matrix[c][r];
      matrix[c][r] = value;
    }
  }
  for (const row of matrix) {
    row.reverse();
  }
}
