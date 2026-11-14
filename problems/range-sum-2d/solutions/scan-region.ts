export class NumMatrix {
  private readonly matrix: number[][];

  constructor(matrix: number[][]) {
    this.matrix = matrix;
  }

  sumRegion(row1: number, col1: number, row2: number, col2: number): number {
    let total = 0;
    for (let row = row1; row <= row2; row++) {
      const cells = this.matrix[row];
      for (let col = col1; col <= col2; col++) {
        total += cells[col];
      }
    }
    return total;
  }
}
