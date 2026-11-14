const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function exist(board: string[][], word: string): boolean {
  const rows = board.length;
  const cols = board[0].length;
  const visited = Array.from({ length: rows }, () => new Array<boolean>(cols).fill(false));
  // Whether word[k..] can be spelled by a walk that starts at (r, c).
  const spellsFrom = (r: number, c: number, k: number): boolean => {
    if (r < 0 || r >= rows || c < 0 || c >= cols || visited[r][c] || board[r][c] !== word[k]) {
      return false;
    }
    if (k === word.length - 1) {
      return true;
    }
    visited[r][c] = true;
    const found = STEPS.some(([dr, dc]) => spellsFrom(r + dr, c + dc, k + 1));
    visited[r][c] = false;
    return found;
  };
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (spellsFrom(r, c, 0)) {
        return true;
      }
    }
  }
  return false;
}
