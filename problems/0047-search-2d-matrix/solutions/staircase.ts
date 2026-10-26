export function searchMatrix(matrix: number[][], target: number): boolean {
  // Everything left of the current cell in its row is smaller or equal; everything
  // below it in its column is larger or equal.
  let row = 0;
  let column = matrix[0].length - 1;
  while (row < matrix.length && column >= 0) {
    const value = matrix[row][column];
    if (value === target) {
      return true;
    }
    if (value > target) {
      column--;
    } else {
      row++;
    }
  }
  return false;
}
