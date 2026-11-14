export function spiralOrder(matrix: number[][]): number[] {
  let top = 0;
  let bottom = matrix.length - 1;
  let left = 0;
  let right = matrix[0].length - 1;
  const order: number[] = [];
  while (top <= bottom && left <= right) {
    for (let c = left; c <= right; c++) order.push(matrix[top][c]);
    for (let r = top + 1; r <= bottom; r++) order.push(matrix[r][right]);
    // Only a ring with two rows and two columns has a bottom row and left column of its own.
    if (top < bottom && left < right) {
      for (let c = right - 1; c >= left; c--) order.push(matrix[bottom][c]);
      for (let r = bottom - 1; r > top; r--) order.push(matrix[r][left]);
    }
    top++;
    bottom--;
    left++;
    right--;
  }
  return order;
}
