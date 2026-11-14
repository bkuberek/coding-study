export class NumMatrix {
  // prefix[r][c] is the sum of the sub-grid of rows 0..r-1 and columns 0..c-1.
  private readonly prefix: number[][];

  constructor(matrix: number[][]) {
    const rows = matrix.length;
    const cols = matrix[0].length;
    this.prefix = Array.from({ length: rows + 1 }, () => new Array<number>(cols + 1).fill(0));
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        this.prefix[r + 1][c + 1] =
          matrix[r][c] + this.prefix[r][c + 1] + this.prefix[r + 1][c] - this.prefix[r][c];
      }
    }
  }

  sumRegion(row1: number, col1: number, row2: number, col2: number): number {
    const p = this.prefix;
    return p[row2 + 1][col2 + 1] - p[row1][col2 + 1] - p[row2 + 1][col1] + p[row1][col1];
  }
}
