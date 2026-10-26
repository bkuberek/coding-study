class DisjointSet {
  private readonly parent: Int32Array;
  private readonly rank: Uint8Array;

  constructor(count: number) {
    this.parent = Int32Array.from({ length: count }, (_, i) => i);
    this.rank = new Uint8Array(count);
  }

  find(cell: number): number {
    let root = cell;
    while (this.parent[root] !== root) root = this.parent[root];
    while (this.parent[cell] !== root) {
      const next = this.parent[cell];
      this.parent[cell] = root;
      cell = next;
    }
    return root;
  }

  union(a: number, b: number): void {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) return;
    if (this.rank[rootA] < this.rank[rootB]) [rootA, rootB] = [rootB, rootA];
    this.parent[rootB] = rootA;
    if (this.rank[rootA] === this.rank[rootB]) this.rank[rootA]++;
  }
}

export function solve(board: string[][]): void {
  const rows = board.length;
  const cols = board[0].length;
  const edge = rows * cols; // a virtual node that every 'O' on the edge joins
  const sets = new DisjointSet(rows * cols + 1);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (board[r][c] !== "O") continue;
      const cell = r * cols + c;
      if (r === 0 || r === rows - 1 || c === 0 || c === cols - 1) sets.union(cell, edge);
      if (c + 1 < cols && board[r][c + 1] === "O") sets.union(cell, cell + 1);
      if (r + 1 < rows && board[r + 1][c] === "O") sets.union(cell, cell + cols);
    }
  }
  const edgeRoot = sets.find(edge);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (board[r][c] === "O" && sets.find(r * cols + c) !== edgeRoot) board[r][c] = "X";
    }
  }
}
