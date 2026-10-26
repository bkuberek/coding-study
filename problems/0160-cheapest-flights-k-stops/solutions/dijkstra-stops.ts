type State = [price: number, city: number, used: number];

// A binary min-heap ordered by price: TypeScript has no built-in priority queue.
class MinHeap {
  private readonly items: State[] = [];

  get size(): number {
    return this.items.length;
  }

  push(state: State): void {
    const items = this.items;
    items.push(state);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent][0] <= items[child][0]) break;
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): State {
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

export function findCheapestPrice(n: number, flights: number[][], src: number, dst: number, k: number): number {
  const graph: [number, number][][] = Array.from({ length: n }, () => []);
  for (const [start, end, cost] of flights) graph[start].push([end, cost]);
  // fewest[c] is the fewest flights with which c was settled so far. States leave the heap in
  // order of price, so a later state for c is useful only if it used fewer flights.
  const fewest = new Array<number>(n).fill(k + 2);
  const heap = new MinHeap();
  heap.push([0, src, 0]);
  while (heap.size > 0) {
    const [price, city, used] = heap.pop();
    if (city === dst) return price;
    if (used >= fewest[city]) continue;
    fewest[city] = used;
    if (used === k + 1) continue; // no flights left
    for (const [neighbor, cost] of graph[city]) heap.push([price + cost, neighbor, used + 1]);
  }
  return -1;
}
