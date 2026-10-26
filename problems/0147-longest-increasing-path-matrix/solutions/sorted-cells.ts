export function longestIncreasingPath(matrix: number[][]): number {
  const rows = matrix.length;
  const columns = matrix[0].length;
  // Cells are numbered r * columns + c; longest[cell] is the longest path starting there.
  const value = (cell: number): number => matrix[Math.floor(cell / columns)][cell % columns];
  const longest = new Int32Array(rows * columns).fill(1);
  // Every larger neighbor comes earlier in decreasing order of value, so its entry is final
  // when the cell is processed. Equal neighbors are never steps, so ties may go either way.
  const order = Array.from({ length: rows * columns }, (_, cell) => cell).sort(
    (a, b) => value(b) - value(a),
  );
  let answer = 1;
  for (const cell of order) {
    const r = Math.floor(cell / columns);
    const c = cell % columns;
    const neighbors: Array<[number, number]> = [
      [r + 1, c],
      [r - 1, c],
      [r, c + 1],
      [r, c - 1],
    ];
    for (const [nr, nc] of neighbors) {
      if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c]) {
        longest[cell] = Math.max(longest[cell], 1 + longest[nr * columns + nc]);
      }
    }
    answer = Math.max(answer, longest[cell]);
  }
  return answer;
}
