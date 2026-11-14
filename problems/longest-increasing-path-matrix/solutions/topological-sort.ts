export function longestIncreasingPath(matrix: number[][]): number {
  const rows = matrix.length;
  const columns = matrix[0].length;
  const steps = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ];
  // Cells are numbered r * columns + c. larger[cell] counts the neighbors a path could still
  // step up to from that cell.
  const larger = new Int8Array(rows * columns);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < columns; c++) {
      for (const [dr, dc] of steps) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] > matrix[r][c]) {
          larger[r * columns + c]++;
        }
      }
    }
  }
  // Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors are
  // all gone. A cell removed in round k starts a longest path of exactly k cells.
  let layer: number[] = [];
  for (let cell = 0; cell < rows * columns; cell++) {
    if (larger[cell] === 0) {
      layer.push(cell);
    }
  }
  let rounds = 0;
  while (layer.length > 0) {
    rounds++;
    const nextLayer: number[] = [];
    for (const cell of layer) {
      const r = Math.floor(cell / columns);
      const c = cell % columns;
      for (const [dr, dc] of steps) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < rows && nc >= 0 && nc < columns && matrix[nr][nc] < matrix[r][c]) {
          const neighbor = nr * columns + nc;
          larger[neighbor]--;
          if (larger[neighbor] === 0) {
            nextLayer.push(neighbor);
          }
        }
      }
    }
    layer = nextLayer;
  }
  return rounds;
}
