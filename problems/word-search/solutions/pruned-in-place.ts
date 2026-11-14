const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];
const USED = "#";

function letterCounts(letters: Iterable<string>): Map<string, number> {
  const counts = new Map<string, number>();
  for (const letter of letters) {
    counts.set(letter, (counts.get(letter) ?? 0) + 1);
  }
  return counts;
}

export function exist(board: string[][], word: string): boolean {
  const rows = board.length;
  const cols = board[0].length;
  const available = letterCounts(board.flat());
  for (const [letter, needed] of letterCounts(word)) {
    if ((available.get(letter) ?? 0) < needed) {
      return false;
    }
  }
  // A walk read backwards is also a walk: start from whichever end is rarer on the board.
  const target =
    (available.get(word[0]) ?? 0) > (available.get(word[word.length - 1]) ?? 0)
      ? [...word].reverse().join("")
      : word;
  const spellsFrom = (r: number, c: number, k: number): boolean => {
    if (board[r][c] !== target[k]) {
      return false;
    }
    if (k === target.length - 1) {
      return true;
    }
    board[r][c] = USED;
    const found = STEPS.some(([dr, dc]) => {
      const nr = r + dr;
      const nc = c + dc;
      return nr >= 0 && nr < rows && nc >= 0 && nc < cols && spellsFrom(nr, nc, k + 1);
    });
    board[r][c] = target[k];
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
