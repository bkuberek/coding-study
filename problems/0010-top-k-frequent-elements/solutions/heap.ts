type Entry = { count: number; value: number };

// A binary min-heap ordered by count: TypeScript has no built-in priority queue.
class MinHeap {
  private readonly items: Entry[] = [];

  get size(): number {
    return this.items.length;
  }

  peek(): Entry {
    return this.items[0];
  }

  push(entry: Entry): void {
    this.items.push(entry);
    let child = this.items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (this.items[parent].count <= this.items[child].count) {
        break;
      }
      this.swap(parent, child);
      child = parent;
    }
  }

  replaceRoot(entry: Entry): void {
    this.items[0] = entry;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let smallest = parent;
      if (left < this.items.length && this.items[left].count < this.items[smallest].count) {
        smallest = left;
      }
      if (right < this.items.length && this.items[right].count < this.items[smallest].count) {
        smallest = right;
      }
      if (smallest === parent) {
        return;
      }
      this.swap(parent, smallest);
      parent = smallest;
    }
  }

  values(): number[] {
    return this.items.map((entry) => entry.value);
  }

  private swap(i: number, j: number): void {
    [this.items[i], this.items[j]] = [this.items[j], this.items[i]];
  }
}

export function topKFrequent(nums: number[], k: number): number[] {
  const counts = new Map<number, number>();
  for (const value of nums) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  const heap = new MinHeap();
  for (const [value, count] of counts) {
    if (heap.size < k) {
      heap.push({ count, value });
    } else if (count > heap.peek().count) {
      heap.replaceRoot({ count, value });
    }
  }
  return heap.values();
}
