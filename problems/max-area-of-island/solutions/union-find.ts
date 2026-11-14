class DisjointSet {
  private readonly parent: Int32Array;
  private readonly size: Int32Array;

  constructor(count: number) {
    this.parent = Int32Array.from({ length: count }, (_, i) => i);
    this.size = new Int32Array(count).fill(1);
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

  /** Merges the groups of a and b and returns the size of the merged group. */
  union(a: number, b: number): number {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA !== rootB) {
      if (this.size[rootA] < this.size[rootB]) [rootA, rootB] = [rootB, rootA];
      this.parent[rootB] = rootA;
      this.size[rootA] += this.size[rootB];
    }
    return this.size[rootA];
  }
}

export function maxAreaOfIsland(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const sets = new DisjointSet(rows * cols);
  let best = 0;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      if (grid[row][col] !== 1) continue;
      const cell = row * cols + col;
      best = Math.max(best, 1);
      if (col + 1 < cols && grid[row][col + 1] === 1) best = Math.max(best, sets.union(cell, cell + 1));
      if (row + 1 < rows && grid[row + 1][col] === 1) best = Math.max(best, sets.union(cell, cell + cols));
    }
  }
  return best;
}
