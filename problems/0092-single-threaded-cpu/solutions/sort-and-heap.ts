// A binary min-heap of task indexes, ordered by processing time, then index.
class TaskHeap {
  private readonly items: number[] = [];
  private readonly tasks: number[][];

  constructor(tasks: number[][]) {
    this.tasks = tasks;
  }

  get size(): number {
    return this.items.length;
  }

  push(index: number): void {
    const items = this.items;
    items.push(index);
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

  private before(a: number, b: number): boolean {
    const difference = this.tasks[a][1] - this.tasks[b][1];
    return difference < 0 || (difference === 0 && a < b);
  }
}

export function getOrder(tasks: number[][]): number[] {
  const arrivals = tasks.map((_, index) => index).sort((a, b) => tasks[a][0] - tasks[b][0]);
  const waiting = new TaskHeap(tasks);
  let time = 0;
  let next = 0;
  const order: number[] = [];
  while (order.length < tasks.length) {
    if (waiting.size === 0 && time < tasks[arrivals[next]][0]) {
      time = tasks[arrivals[next]][0]; // idle until the next arrival
    }
    while (next < tasks.length && tasks[arrivals[next]][0] <= time) {
      waiting.push(arrivals[next++]);
    }
    const index = waiting.pop();
    time += tasks[index][1];
    order.push(index);
  }
  return order;
}
