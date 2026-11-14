const SIDE = 9;
const BOX = 3;
const EMPTY = ".";

// Whether another cell in the same row, column or box holds `digit`.
function repeats(board: string[][], row: number, column: number, digit: string): boolean {
  const top = row - (row % BOX);
  const left = column - (column % BOX);
  for (let i = 0; i < SIDE; i++) {
    if (i !== column && board[row][i] === digit) {
      return true;
    }
    if (i !== row && board[i][column] === digit) {
      return true;
    }
    const boxRow = top + Math.floor(i / BOX);
    const boxColumn = left + (i % BOX);
    if ((boxRow !== row || boxColumn !== column) && board[boxRow][boxColumn] === digit) {
      return true;
    }
  }
  return false;
}

export function isValidSudoku(board: string[][]): boolean {
  for (let row = 0; row < SIDE; row++) {
    for (let column = 0; column < SIDE; column++) {
      const digit = board[row][column];
      if (digit !== EMPTY && repeats(board, row, column, digit)) {
        return false;
      }
    }
  }
  return true;
}
