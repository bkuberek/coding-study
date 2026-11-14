type Entry = [distance: number, city: number];

// A binary min-heap ordered by distance: TypeScript has no built-in priority queue.
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

export function findTheCity(n: number, edges: number[][], distanceThreshold: number): number {
  const graph: [number, number][][] = Array.from({ length: n }, () => []);
  for (const [a, b, w] of edges) {
    graph[a].push([b, w]);
    graph[b].push([a, w]);
  }

  // Counts the other cities within the threshold, never pushing a distance beyond it.
  const reachable = (source: number): number => {
    const settled = new Uint8Array(n);
    const heap = new MinHeap();
    heap.push([0, source]);
    let count = -1;
    while (heap.size > 0) {
      const [distance, city] = heap.pop();
      if (settled[city] === 1) continue;
      settled[city] = 1;
      count++;
      for (const [neighbor, w] of graph[city]) {
        if (settled[neighbor] === 0 && distance + w <= distanceThreshold) heap.push([distance + w, neighbor]);
      }
    }
    return count;
  };

  let bestCity = -1;
  let bestCount = n + 1;
  for (let city = 0; city < n; city++) {
    const count = reachable(city);
    // `<=` lets a later city win a tie.
    if (count <= bestCount) {
      bestCity = city;
      bestCount = count;
    }
  }
  return bestCity;
}
