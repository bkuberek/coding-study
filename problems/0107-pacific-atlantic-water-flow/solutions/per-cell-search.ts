export function pacificAtlantic(heights: number[][]): number[][] {
  const rows = heights.length;
  const cols = heights[0].length;
  const seen = new Int32Array(rows * cols).fill(-1);

  // `seen[cell] === start` marks cells visited by the search from `start`, so one array
  // serves every search without clearing it in between.
  const drainsToBoth = (start: number): boolean => {
    let pacific = false;
    let atlantic = false;
    seen[start] = start;
    const stack = [start];
    while (stack.length > 0) {
      const cell = stack.pop()!;
      const r = Math.floor(cell / cols);
      const c = cell % cols;
      pacific ||= r === 0 || c === 0;
      atlantic ||= r === rows - 1 || c === cols - 1;
      if (pacific && atlantic) return true;
      for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const next = nr * cols + nc;
        if (seen[next] !== start && heights[nr][nc] <= heights[r][c]) {
          seen[next] = start;
          stack.push(next);
        }
      }
    }
    return false;
  };

  const cells: number[][] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (drainsToBoth(r * cols + c)) cells.push([r, c]);
    }
  }
  return cells;
}
