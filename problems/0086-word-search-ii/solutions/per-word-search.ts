const USED = "#";
const STEPS: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]];

export function findWords(board: string[][], words: string[]): string[] {
  return words.filter((word) => onBoard(board, word));
}

function onBoard(board: string[][], word: string): boolean {
  const rows = board.length;
  const cols = board[0].length;
  /** Can word[position..] be spelled starting at this cell? */
  const trace = (row: number, col: number, position: number): boolean => {
    if (board[row][col] !== word[position]) return false;
    if (position === word.length - 1) return true;
    board[row][col] = USED;
    let found = false;
    for (const [dr, dc] of STEPS) {
      const r = row + dr;
      const c = col + dc;
      if (r >= 0 && r < rows && c >= 0 && c < cols && trace(r, c, position + 1)) {
        found = true;
        break;
      }
    }
    board[row][col] = word[position];
    return found;
  };
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      if (trace(row, col, 0)) return true;
    }
  }
  return false;
}
