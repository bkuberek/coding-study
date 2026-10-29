// An employee's next interval: its start, the employee, and its position in their list.
type Entry = [start: number, person: number, position: number];

export function employeeFreeTime(schedule: number[][][]): number[][] {
  const upcoming = new MinHeap();
  schedule.forEach((shifts, person) => upcoming.push([shifts[0][0], person, 0]));
  const free: number[][] = [];
  let busyUntil = upcoming.peek()[0];
  while (upcoming.size() > 0) {
    const [start, person, position] = upcoming.pop();
    if (start > busyUntil) {
      free.push([busyUntil, start]);
    }
    busyUntil = Math.max(busyUntil, schedule[person][position][1]);
    if (position + 1 < schedule[person].length) {
      upcoming.push([schedule[person][position + 1][0], person, position + 1]);
    }
  }
  return free;
}

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
      if (!MinHeap.before(items[child], items[parent])) {
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
        if (left < items.length && MinHeap.before(items[left], items[smallest])) {
          smallest = left;
        }
        if (right < items.length && MinHeap.before(items[right], items[smallest])) {
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

  // Earlier start first; the employee index breaks ties.
  private static before(a: Entry, b: Entry): boolean {
    return a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
  }
}
