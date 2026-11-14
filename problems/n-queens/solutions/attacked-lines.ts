function drawBoard(queenColumn: number[]): string[] {
  const n = queenColumn.length;
  return queenColumn.map((col) => ".".repeat(col) + "Q" + ".".repeat(n - col - 1));
}

export function solveNQueens(n: number): string[][] {
  const boards: string[][] = [];
  const queenColumn: number[] = [];
  const columns = new Array<boolean>(n).fill(false);
  // Squares on one diagonal share row - col (shifted by n - 1 to index from 0); on one
  // anti-diagonal they share row + col.
  const diagonals = new Array<boolean>(2 * n - 1).fill(false);
  const antiDiagonals = new Array<boolean>(2 * n - 1).fill(false);
  const place = (row: number): void => {
    if (row === n) {
      boards.push(drawBoard(queenColumn));
      return;
    }
    for (let col = 0; col < n; col++) {
      const diagonal = row - col + n - 1;
      const antiDiagonal = row + col;
      if (columns[col] || diagonals[diagonal] || antiDiagonals[antiDiagonal]) {
        continue;
      }
      columns[col] = diagonals[diagonal] = antiDiagonals[antiDiagonal] = true;
      queenColumn.push(col);
      place(row + 1);
      queenColumn.pop();
      columns[col] = diagonals[diagonal] = antiDiagonals[antiDiagonal] = false;
    }
  };
  place(0);
  return boards;
}
