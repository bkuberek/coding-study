export function rotate(matrix: number[][]): void {
  const n = matrix.length;
  for (let layer = 0; layer < Math.floor(n / 2); layer++) {
    const last = n - 1 - layer;
    for (let offset = 0; offset < last - layer; offset++) {
      const top = matrix[layer][layer + offset];
      // left -> top, bottom -> left, right -> bottom, top -> right
      matrix[layer][layer + offset] = matrix[last - offset][layer];
      matrix[last - offset][layer] = matrix[last][last - offset];
      matrix[last][last - offset] = matrix[layer + offset][last];
      matrix[layer + offset][last] = top;
    }
  }
}
