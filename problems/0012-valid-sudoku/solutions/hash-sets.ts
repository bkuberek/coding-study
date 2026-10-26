const SIDE = 9;
const BOX = 3;
const EMPTY = ".";

export function isValidSudoku(board: string[][]): boolean {
  const rows = Array.from({ length: SIDE }, () => new Set<string>());
  const columns = Array.from({ length: SIDE }, () => new Set<string>());
  const boxes = Array.from({ length: SIDE }, () => new Set<string>());
  for (let row = 0; row < SIDE; row++) {
    for (let column = 0; column < SIDE; column++) {
      const digit = board[row][column];
      if (digit === EMPTY) {
        continue;
      }
      const box = Math.floor(row / BOX) * BOX + Math.floor(column / BOX);
      if (rows[row].has(digit) || columns[column].has(digit) || boxes[box].has(digit)) {
        return false;
      }
      rows[row].add(digit);
      columns[column].add(digit);
      boxes[box].add(digit);
    }
  }
  return true;
}
