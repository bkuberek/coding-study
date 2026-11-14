const STEPS: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

export function numIslands2(m: number, n: number, positions: number[][]): number[] {
  const land = new Array<boolean>(m * n).fill(false); // cell r * n + c
  const cells: number[] = []; // every land cell, each once
  const countIslands = (): number => {
    const seen = new Set<number>();
    let islands = 0;
    for (const start of cells) {
      if (seen.has(start)) {
        continue;
      }
      islands++;
      seen.add(start);
      const stack = [start];
      while (stack.length > 0) {
        const cell = stack.pop() as number;
        const r = Math.floor(cell / n);
        const c = cell % n;
        for (const [dr, dc] of STEPS) {
          const nr = r + dr;
          const nc = c + dc;
          const neighbor = nr * n + nc;
          if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[neighbor] && !seen.has(neighbor)) {
            seen.add(neighbor);
            stack.push(neighbor);
          }
        }
      }
    }
    return islands;
  };
  return positions.map(([r, c]) => {
    const cell = r * n + c;
    if (!land[cell]) {
      land[cell] = true;
      cells.push(cell);
    }
    return countIslands();
  });
}
