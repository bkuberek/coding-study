const DIRECTIONS = [
  [0, 1],
  [1, 0],
  [0, -1],
  [-1, 0],
]; // right, down, left, up: clockwise

export function spiralOrder(matrix: number[][]): number[] {
  const rows = matrix.length;
  const cols = matrix[0].length;
  const visited = Array.from({ length: rows }, () => new Array<boolean>(cols).fill(false));
  const order: number[] = [];
  let r = 0;
  let c = 0;
  let heading = 0;
  for (let step = 0; step < rows * cols; step++) {
    order.push(matrix[r][c]);
    visited[r][c] = true;
    let [dr, dc] = DIRECTIONS[heading];
    let nr = r + dr;
    let nc = c + dc;
    if (nr < 0 || nr >= rows || nc < 0 || nc >= cols || visited[nr][nc]) {
      heading = (heading + 1) % 4;
      [dr, dc] = DIRECTIONS[heading];
      nr = r + dr;
      nc = c + dc;
    }
    r = nr;
    c = nc;
  }
  return order;
}
