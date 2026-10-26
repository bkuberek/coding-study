// A binary max-heap of numbers: TypeScript has no built-in priority queue.
class MaxHeap {
  private readonly items: number[];

  constructor(values: number[]) {
    this.items = [...values];
    // Heapify bottom-up: sift down every parent, last parent first. O(n) in total.
    for (let index = (this.items.length >> 1) - 1; index >= 0; index--) {
      this.siftDown(index);
    }
  }

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
      if (items[parent] >= items[child]) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): number {
    const items = this.items;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      this.siftDown(0);
    }
    return top;
  }

  private siftDown(start: number): void {
    const items = this.items;
    let parent = start;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let largest = parent;
      if (left < items.length && items[left] > items[largest]) {
        largest = left;
      }
      if (right < items.length && items[right] > items[largest]) {
        largest = right;
      }
      if (largest === parent) {
        return;
      }
      [items[parent], items[largest]] = [items[largest], items[parent]];
      parent = largest;
    }
  }
}

export function lastStoneWeight(stones: number[]): number {
  const heap = new MaxHeap(stones);
  while (heap.size > 1) {
    const heaviest = heap.pop();
    const second = heap.pop();
    if (heaviest !== second) {
      heap.push(heaviest - second);
    }
  }
  return heap.size === 1 ? heap.peek() : 0;
}
