type Entry = [time: number, node: number];

// A binary min-heap ordered by time: TypeScript has no built-in priority queue.
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

export function networkDelayTime(times: number[][], n: number, k: number): number {
  const graph: [number, number][][] = Array.from({ length: n + 1 }, () => []);
  for (const [u, v, w] of times) graph[u].push([v, w]);
  const arrival = new Array<number>(n + 1).fill(-1);
  const heap = new MinHeap();
  heap.push([0, k]);
  let settled = 0;
  let latest = 0;
  while (heap.size > 0) {
    const [time, node] = heap.pop();
    if (arrival[node] !== -1) continue; // an outdated entry: settled earlier with a smaller time
    arrival[node] = time;
    settled++;
    latest = time;
    for (const [neighbor, w] of graph[node]) {
      if (arrival[neighbor] === -1) heap.push([time + w, neighbor]);
    }
  }
  return settled === n ? latest : -1;
}
