const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function longestIncreasingPath(matrix: number[][]): number {
  const rows = matrix.length;
  const columns = matrix[0].length;
  // longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
  const longest = Array.from({ length: rows }, () => new Int32Array(columns));
  const explore = (r: number, c: number): number => {
    if (longest[r][c] === 0) {
      let best = 1;
      for (const [dr, dc] of STEPS) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c]) {
          best = Math.max(best, 1 + explore(nr, nc));
        }
      }
      longest[r][c] = best;
    }
    return longest[r][c];
  };
  let answer = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      answer = Math.max(answer, explore(r, c));
    }
  }
  return answer;
}
