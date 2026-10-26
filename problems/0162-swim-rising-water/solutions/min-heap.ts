type Entry = [level: number, cell: number];

// A binary min-heap ordered by level: TypeScript has no built-in priority queue.
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

export function swimInWater(grid: number[][]): number {
  const n = grid.length;
  const seen = new Uint8Array(n * n);
  seen[0] = 1;
  // Entries are [highest floor on the route so far, cell index].
  const heap = new MinHeap();
  heap.push([grid[0][0], 0]);
  for (;;) {
    const [level, cell] = heap.pop();
    if (cell === n * n - 1) return level;
    const r = Math.floor(cell / n);
    const c = cell % n;
    for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
      if (nr < 0 || nr >= n || nc < 0 || nc >= n) continue;
      const next = nr * n + nc;
      if (seen[next] === 0) {
        seen[next] = 1;
        heap.push([Math.max(level, grid[nr][nc]), next]);
      }
    }
  }
}
