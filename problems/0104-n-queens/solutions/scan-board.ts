function drawBoard(queenColumn: number[]): string[] {
  const n = queenColumn.length;
  return queenColumn.map((col) => ".".repeat(col) + "Q" + ".".repeat(n - col - 1));
}

export function solveNQueens(n: number): string[][] {
  const boards: string[][] = [];
  // queenColumn[r] is the column of the queen in row r, for the rows placed so far.
  const queenColumn: number[] = [];
  const isSafe = (row: number, col: number): boolean =>
    queenColumn.every(
      (otherCol, otherRow) => col !== otherCol && Math.abs(col - otherCol) !== row - otherRow,
    );
  const place = (row: number): void => {
    if (row === n) {
      boards.push(drawBoard(queenColumn));
      return;
    }
    for (let col = 0; col < n; col++) {
      if (isSafe(row, col)) {
        queenColumn.push(col);
        place(row + 1);
        queenColumn.pop();
      }
    }
  };
  place(0);
  return boards;
}
