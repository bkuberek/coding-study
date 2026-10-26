const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

class DisjointSets {
  private readonly parent: number[];
  private readonly size: number[]; // size[r]: number of cells in the tree rooted at r

  constructor(count: number) {
    this.parent = Array.from({ length: count }, (_, x) => x);
    this.size = new Array<number>(count).fill(1);
  }

  find(x: number): number {
    let root = x;
    while (this.parent[root] !== root) {
      root = this.parent[root];
    }
    while (this.parent[x] !== root) {
      // Path compression: point every node on the path at the root.
      const next = this.parent[x];
      this.parent[x] = root;
      x = next;
    }
    return root;
  }

  // Merges the sets of a and b; false when they were already one set.
  union(a: number, b: number): boolean {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) {
      return false;
    }
    if (this.size[rootA] < this.size[rootB]) {
      [rootA, rootB] = [rootB, rootA];
    }
    this.parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
    this.size[rootA] += this.size[rootB];
    return true;
  }
}

export function numIslands2(m: number, n: number, positions: number[][]): number[] {
  const sets = new DisjointSets(m * n); // cell r * n + c
  const land = new Array<boolean>(m * n).fill(false);
  let islands = 0;
  return positions.map(([r, c]) => {
    const cell = r * n + c;
    if (!land[cell]) {
      land[cell] = true;
      islands++; // a new island, until it merges with its neighbors
      for (const [dr, dc] of STEPS) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr * n + nc] && sets.union(nr * n + nc, cell)) {
          islands--;
        }
      }
    }
    return islands;
  });
}
