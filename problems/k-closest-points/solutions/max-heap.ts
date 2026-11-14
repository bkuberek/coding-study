type Entry = { distance: number; index: number };

// A binary max-heap ordered by distance: TypeScript has no built-in priority queue.
class MaxHeap {
  private readonly items: Entry[] = [];

  get size(): number {
    return this.items.length;
  }

  peek(): Entry {
    return this.items[0];
  }

  push(entry: Entry): void {
    const items = this.items;
    items.push(entry);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent].distance >= items[child].distance) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  replaceRoot(entry: Entry): void {
    const items = this.items;
    items[0] = entry;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let largest = parent;
      if (left < items.length && items[left].distance > items[largest].distance) {
        largest = left;
      }
      if (right < items.length && items[right].distance > items[largest].distance) {
        largest = right;
      }
      if (largest === parent) {
        return;
      }
      [items[parent], items[largest]] = [items[largest], items[parent]];
      parent = largest;
    }
  }

  indexes(): number[] {
    return this.items.map((entry) => entry.index);
  }
}

export function kClosest(points: number[][], k: number): number[][] {
  // The heap keeps the k closest points seen so far; its root is the farthest of them.
  const heap = new MaxHeap();
  points.forEach(([x, y], index) => {
    const entry = { distance: x * x + y * y, index };
    if (heap.size < k) {
      heap.push(entry);
    } else if (entry.distance < heap.peek().distance) {
      heap.replaceRoot(entry);
    }
  });
  return heap.indexes().map((index) => points[index]);
}
