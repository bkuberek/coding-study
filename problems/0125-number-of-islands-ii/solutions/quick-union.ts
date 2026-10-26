const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function numIslands2(m: number, n: number, positions: number[][]): number[] {
  const parent = Array.from({ length: m * n }, (_, x) => x); // cell r * n + c; parent[x] === x marks a root
  const land = new Array<boolean>(m * n).fill(false);
  const find = (x: number): number => {
    while (parent[x] !== x) {
      x = parent[x];
    }
    return x;
  };
  let islands = 0;
  return positions.map(([r, c]) => {
    const cell = r * n + c;
    if (!land[cell]) {
      land[cell] = true;
      islands++; // a new island, until it merges with its neighbors
      for (const [dr, dc] of STEPS) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr * n + nc]) {
          const rootNeighbor = find(nr * n + nc);
          const rootCell = find(cell);
          if (rootNeighbor !== rootCell) {
            parent[rootNeighbor] = rootCell; // no balancing: chains can grow
            islands--;
          }
        }
      }
    }
    return islands;
  });
}
