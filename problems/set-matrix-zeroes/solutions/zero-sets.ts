export function setZeroes(matrix: number[][]): void {
  // Find every row and column to clear before clearing anything.
  const zeroRows = new Set<number>();
  const zeroCols = new Set<number>();
  matrix.forEach((row, r) => {
    row.forEach((value, c) => {
      if (value === 0) {
        zeroRows.add(r);
        zeroCols.add(c);
      }
    });
  });
  matrix.forEach((row, r) => {
    for (let c = 0; c < row.length; c++) {
      if (zeroRows.has(r) || zeroCols.has(c)) {
        row[c] = 0;
      }
    }
  });
}
