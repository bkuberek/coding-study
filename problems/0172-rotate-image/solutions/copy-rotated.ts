export function rotate(matrix: number[][]): void {
  const n = matrix.length;
  // Row r of the rotated image is column r of the original, read from bottom to top.
  const rotated = Array.from({ length: n }, (_, r) =>
    Array.from({ length: n }, (_, c) => matrix[n - 1 - c][r]),
  );
  for (let r = 0; r < n; r++) {
    matrix[r] = rotated[r];
  }
}
