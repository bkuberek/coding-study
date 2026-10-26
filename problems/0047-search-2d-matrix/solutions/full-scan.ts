export function searchMatrix(matrix: number[][], target: number): boolean {
  for (const row of matrix) {
    for (const value of row) {
      if (value === target) {
        return true;
      }
    }
  }
  return false;
}
