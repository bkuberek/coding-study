type Entry = [cost: number, cell: number];

// A binary min-heap ordered by cost: TypeScript has no built-in priority queue.
class MinHeap {
  private readonly items: Entry[] = [];

  get size(): number {
    return this.items.length;
  }

  push(entry: Entry): void {
    const items = this.items;
    items.push(entry);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent][0] <= items[child][0]) break;
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): Entry {
    const items = this.items;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      let parent = 0;
      for (;;) {
        const left = 2 * parent + 1;
        const right = left + 1;
        let smallest = parent;
        if (left < items.length && items[left][0] < items[smallest][0]) smallest = left;
        if (right < items.length && items[right][0] < items[smallest][0]) smallest = right;
        if (smallest === parent) break;
        [items[parent], items[smallest]] = [items[smallest], items[parent]];
        parent = smallest;
      }
    }
    return top;
  }
}

export function minimumObstacles(grid: number[][]): number {
  const rows = grid.length;
  const cols = grid[0].length;
  const goal = rows * cols - 1;
  const settled = new Uint8Array(rows * cols);
  // Entries are [removals so far, cell index]; entering a cell costs its own value.
  const heap = new MinHeap();
  heap.push([0, 0]);
  for (;;) {
    const [cost, cell] = heap.pop();
    if (settled[cell] === 1) continue; // an outdated entry: settled earlier at a lower cost
    settled[cell] = 1;
    if (cell === goal) return cost;
    const r = Math.floor(cell / cols);
    const c = cell % cols;
    for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
      if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
      const next = nr * cols + nc;
      if (settled[next] === 0) heap.push([cost + grid[nr][nc], next]);
    }
  }
}
