export function minInterval(intervals: number[][], queries: number[]): number[] {
  const byLeft = [...intervals].sort((a, b) => a[0] - b[0]);
  const order = queries.map((_, index) => index).sort((a, b) => queries[a] - queries[b]);
  const answer = new Array<number>(queries.length).fill(-1);
  // Entries are [size, right] of intervals that start at or before the current query.
  const candidates = new MinHeap();
  let added = 0;
  for (const index of order) {
    const query = queries[index];
    while (added < byLeft.length && byLeft[added][0] <= query) {
      const [left, right] = byLeft[added++];
      candidates.push([right - left + 1, right]);
    }
    // An interval that ends before this query also ends before every later one.
    while (candidates.size() > 0 && candidates.peek()[1] < query) {
      candidates.pop();
    }
    if (candidates.size() > 0) {
      answer[index] = candidates.peek()[0];
    }
  }
  return answer;
}

type Entry = [number, number];

// Binary min-heap ordered by size, then by right end.
class MinHeap {
  private readonly items: Entry[] = [];

  size(): number {
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
      if (!before(items[child], items[parent])) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): Entry {
    const items = this.items;
    const top = items[0];
    const last = items.pop() as Entry;
    if (items.length > 0) {
      items[0] = last;
      let parent = 0;
      for (;;) {
        const left = 2 * parent + 1;
        const right = left + 1;
        let smallest = parent;
        if (left < items.length && before(items[left], items[smallest])) {
          smallest = left;
        }
        if (right < items.length && before(items[right], items[smallest])) {
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

function before(a: Entry, b: Entry): boolean {
  return a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
}
