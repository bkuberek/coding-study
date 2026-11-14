export function searchMatrix(matrix: number[][], target: number): boolean {
  const columns = matrix[0].length;
  let low = 0;
  let high = matrix.length * columns - 1;
  while (low <= high) {
    const middle = (low + high) >>> 1;
    const value = matrix[Math.floor(middle / columns)][middle % columns];
    if (value === target) {
      return true;
    }
    if (value < target) {
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return false;
}
