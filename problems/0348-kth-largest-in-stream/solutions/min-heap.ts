// A min-heap of numbers stored in an array: the children of index i are 2i + 1 and 2i + 2, and
// every entry is no larger than its children, so index 0 holds the smallest.
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
      if (items[parent] <= items[child]) break;
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  // Removes the smallest entry and puts `value` in its place, in one sift down.
  replaceTop(value: number): void {
    const items = this.items;
    items[0] = value;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let smallest = parent;
      if (left < items.length && items[left] < items[smallest]) smallest = left;
      if (right < items.length && items[right] < items[smallest]) smallest = right;
      if (smallest === parent) return;
      [items[parent], items[smallest]] = [items[smallest], items[parent]];
      parent = smallest;
    }
  }
}

export class KthLargestTracker {
  private readonly k: number;
  // The k largest numbers seen so far, with the smallest of them on top.
  private readonly top = new MinHeap();

  constructor(k: number, nums: number[]) {
    this.k = k;
    for (const value of nums) this.offer(value);
  }

  add(value: number): number {
    this.offer(value);
    return this.top.peek();
  }

  private offer(value: number): void {
    if (this.top.size < this.k) {
      this.top.push(value);
    } else if (value > this.top.peek()) {
      // Only a number larger than the current kth largest can join the top k.
      this.top.replaceTop(value);
    }
  }
}
