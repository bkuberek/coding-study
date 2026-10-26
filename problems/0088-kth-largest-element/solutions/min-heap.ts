// A binary min-heap of numbers: TypeScript has no built-in priority queue.
class MinHeap {
  private readonly items: number[] = [];

  get size(): number {
    return this.items.length;
  }

  peek(): number {
    return this.items[0];
  }

  push(value: number): void {
    const items = this.items;
    items.push(value);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent] <= items[child]) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  replaceRoot(value: number): void {
    const items = this.items;
    items[0] = value;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let smallest = parent;
      if (left < items.length && items[left] < items[smallest]) {
        smallest = left;
      }
      if (right < items.length && items[right] < items[smallest]) {
        smallest = right;
      }
      if (smallest === parent) {
        return;
      }
      [items[parent], items[smallest]] = [items[smallest], items[parent]];
      parent = smallest;
    }
  }
}

export function findKthLargest(nums: number[], k: number): number {
  // The heap keeps the k largest values seen so far; its root is the smallest of them.
  const heap = new MinHeap();
  for (const value of nums) {
    if (heap.size < k) {
      heap.push(value);
    } else if (value > heap.peek()) {
      heap.replaceRoot(value);
    }
  }
  return heap.peek();
}
