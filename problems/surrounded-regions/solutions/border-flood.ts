const SAFE = "S";

export function solve(board: string[][]): void {
  const rows = board.length;
  const cols = board[0].length;
  // Every 'O' on the edge is safe; so is everything connected to one of them.
  const stack: number[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const onEdge = r === 0 || r === rows - 1 || c === 0 || c === cols - 1;
      if (onEdge && board[r][c] === "O") {
        board[r][c] = SAFE;
        stack.push(r * cols + c);
      }
    }
  }
  while (stack.length > 0) {
    const cell = stack.pop()!;
    const r = Math.floor(cell / cols);
    const c = cell % cols;
    for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && board[nr][nc] === "O") {
        board[nr][nc] = SAFE;
        stack.push(nr * cols + nc);
      }
    }
  }
  for (const row of board) {
    for (let c = 0; c < cols; c++) {
      row[c] = row[c] === SAFE ? "O" : "X";
    }
  }
}
