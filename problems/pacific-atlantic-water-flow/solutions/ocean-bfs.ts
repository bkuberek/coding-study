export function pacificAtlantic(heights: number[][]): number[][] {
  const rows = heights.length;
  const cols = heights[0].length;

  // Cells whose water can reach a coast: search uphill from all its cells at once.
  const climb = (isCoast: (r: number, c: number) => boolean): Uint8Array => {
    const reached = new Uint8Array(rows * cols);
    const queue: number[] = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (isCoast(r, c)) {
          reached[r * cols + c] = 1;
          queue.push(r * cols + c);
        }
      }
    }
    for (let head = 0; head < queue.length; head++) {
      const r = Math.floor(queue[head] / cols);
      const c = queue[head] % cols;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const next = nr * cols + nc;
        if (reached[next] === 0 && heights[nr][nc] >= heights[r][c]) {
          reached[next] = 1;
          queue.push(next);
        }
      }
    }
    return reached;
  };

  const pacific = climb((r, c) => r === 0 || c === 0);
  const atlantic = climb((r, c) => r === rows - 1 || c === cols - 1);
  const cells: number[][] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (pacific[r * cols + c] === 1 && atlantic[r * cols + c] === 1) cells.push([r, c]);
    }
  }
  return cells;
}
