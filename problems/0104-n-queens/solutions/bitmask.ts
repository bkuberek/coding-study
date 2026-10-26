function drawBoard(queenColumn: number[]): string[] {
  const n = queenColumn.length;
  return queenColumn.map((col) => ".".repeat(col) + "Q" + ".".repeat(n - col - 1));
}

export function solveNQueens(n: number): string[][] {
  const full = (1 << n) - 1;
  const boards: string[][] = [];
  const queenColumn: number[] = [];
  // Each mask marks the squares of the current row attacked along one kind of line.
  const place = (columns: number, diagonals: number, antiDiagonals: number): void => {
    if (columns === full) {
      boards.push(drawBoard(queenColumn));
      return;
    }
    let free = full & ~(columns | diagonals | antiDiagonals);
    while (free !== 0) {
      const bit = free & -free; // lowest free square
      free ^= bit;
      queenColumn.push(31 - Math.clz32(bit));
      // Moving one row down shifts each diagonal attack one column over.
      place(columns | bit, ((diagonals | bit) << 1) & full, (antiDiagonals | bit) >> 1);
      queenColumn.pop();
    }
  };
  place(0, 0, 0);
  return boards;
}
