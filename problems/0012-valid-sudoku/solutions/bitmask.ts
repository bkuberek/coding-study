const SIDE = 9;
const BOX = 3;
const EMPTY = ".";

export function isValidSudoku(board: string[][]): boolean {
  // Bit d - 1 of a mask is set once digit d has been seen in that row, column or box.
  const rows = new Int32Array(SIDE);
  const columns = new Int32Array(SIDE);
  const boxes = new Int32Array(SIDE);
  for (let row = 0; row < SIDE; row++) {
    for (let column = 0; column < SIDE; column++) {
      const cell = board[row][column];
      if (cell === EMPTY) {
        continue;
      }
      const bit = 1 << (Number(cell) - 1);
      const box = Math.floor(row / BOX) * BOX + Math.floor(column / BOX);
      if ((rows[row] | columns[column] | boxes[box]) & bit) {
        return false;
      }
      rows[row] |= bit;
      columns[column] |= bit;
      boxes[box] |= bit;
    }
  }
  return true;
}
