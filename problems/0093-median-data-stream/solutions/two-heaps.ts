// A binary heap of numbers; `before(a, b)` says whether a belongs nearer the root than b.
// TypeScript has no built-in priority queue.
class Heap {
  private readonly items: number[] = [];
  private readonly before: (a: number, b: number) => boolean;

  constructor(before: (a: number, b: number) => boolean) {
    this.before = before;
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
      if (!this.before(items[child], items[parent])) {
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
      let parent = 0;
      for (;;) {
        const left = 2 * parent + 1;
        const right = left + 1;
        let first = parent;
        if (left < items.length && this.before(items[left], items[first])) {
          first = left;
        }
        if (right < items.length && this.before(items[right], items[first])) {
          first = right;
        }
        if (first === parent) {
          break;
        }
        [items[parent], items[first]] = [items[first], items[parent]];
        parent = first;
      }
    }
    return top;
  }
}

export class MedianFinder {
  // low: the smaller half, largest on top. high: the larger half, smallest on top.
  // low holds as many values as high, or one more.
  private readonly low = new Heap((a, b) => a > b);
  private readonly high = new Heap((a, b) => a < b);

  addNum(num: number): void {
    // Route the number through low so that every value in low stays <= every value in high.
    this.low.push(num);
    this.high.push(this.low.pop());
    if (this.high.size > this.low.size) {
      this.low.push(this.high.pop());
    }
  }

  findMedian(): number {
    if (this.low.size > this.high.size) {
      return this.low.peek();
    }
    return (this.low.peek() + this.high.peek()) / 2;
  }
}
