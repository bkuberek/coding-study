class IndexMaxHeap {
  private readonly heap: number[] = [];
  private readonly values: number[];

  constructor(values: number[]) {
    this.values = values;
  }

  peek(): number {
    return this.heap[0];
  }

  push(index: number): void {
    const heap = this.heap;
    heap.push(index);
    let child = heap.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (this.values[heap[parent]] >= this.values[heap[child]]) {
        break;
      }
      [heap[parent], heap[child]] = [heap[child], heap[parent]];
      child = parent;
    }
  }

  pop(): void {
    const heap = this.heap;
    const last = heap.pop()!;
    if (heap.length === 0) {
      return;
    }
    heap[0] = last;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let largest = parent;
      if (left < heap.length && this.values[heap[left]] > this.values[heap[largest]]) {
        largest = left;
      }
      if (right < heap.length && this.values[heap[right]] > this.values[heap[largest]]) {
        largest = right;
      }
      if (largest === parent) {
        return;
      }
      [heap[parent], heap[largest]] = [heap[largest], heap[parent]];
      parent = largest;
    }
  }
}

export function maxSlidingWindow(nums: number[], k: number): number[] {
  const heap = new IndexMaxHeap(nums);
  const maxima: number[] = [];
  for (let right = 0; right < nums.length; right++) {
    heap.push(right);
    if (right >= k - 1) {
      while (heap.peek() <= right - k) {
        heap.pop();
      }
      maxima.push(nums[heap.peek()]);
    }
  }
  return maxima;
}
