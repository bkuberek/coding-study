const USED = "#";
const STEPS: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const CODE_OF_A = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array(26).fill(null);
  word: string | null = null;
}

export function findWords(board: string[][], words: string[]): string[] {
  const root = new TrieNode();
  for (const word of words) {
    let node = root;
    for (let i = 0; i < word.length; i++) {
      node = node.children[word.charCodeAt(i) - CODE_OF_A] ??= new TrieNode();
    }
    node.word = word;
  }
  const rows = board.length;
  const cols = board[0].length;
  const found: string[] = [];
  const explore = (row: number, col: number, parent: TrieNode): void => {
    const letter = board[row][col];
    if (letter === USED) return;
    const node = parent.children[letter.charCodeAt(0) - CODE_OF_A];
    if (node === null) return;
    if (node.word !== null) {
      found.push(node.word);
      node.word = null;
    }
    board[row][col] = USED;
    for (const [dr, dc] of STEPS) {
      const r = row + dr;
      const c = col + dc;
      if (r >= 0 && r < rows && c >= 0 && c < cols) explore(r, c, node);
    }
    board[row][col] = letter;
  };
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) explore(row, col, root);
  }
  return found;
}
