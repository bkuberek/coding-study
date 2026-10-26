export function minMeetingRooms(intervals: number[][]): number {
  const byStart = [...intervals].sort((a, b) => a[0] - b[0]);
  // End times of the meetings currently holding a room; the smallest is on top.
  const ends = new MinHeap();
  for (const [start, end] of byStart) {
    if (ends.size() > 0 && ends.peek() <= start) {
      ends.pop();
    }
    ends.push(end);
  }
  return ends.size();
}

class MinHeap {
  private readonly items: number[] = [];

  size(): number {
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

  pop(): number {
    const items = this.items;
    const top = items[0];
    const last = items.pop() as number;
    if (items.length > 0) {
      items[0] = last;
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
          break;
        }
        [items[parent], items[smallest]] = [items[smallest], items[parent]];
        parent = smallest;
      }
    }
    return top;
  }
}
