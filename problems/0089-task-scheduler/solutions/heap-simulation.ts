// A binary max-heap of numbers: TypeScript has no built-in priority queue.
class MaxHeap {
  private readonly items: number[] = [];

  get size(): number {
    return this.items.length;
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
      let parent = 0;
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
          break;
        }
        [items[parent], items[largest]] = [items[largest], items[parent]];
        parent = largest;
      }
    }
    return top;
  }
}

export function leastInterval(tasks: string[], cooldown: number): number {
  const counts = new Map<string, number>();
  for (const task of tasks) {
    counts.set(task, (counts.get(task) ?? 0) + 1);
  }
  // Remaining counts of the tasks that may run now.
  const ready = new MaxHeap();
  for (const count of counts.values()) {
    ready.push(count);
  }
  // Tasks that just ran, as [time they may run again, remaining count], in time order.
  const cooling: [number, number][] = [];
  let head = 0;
  let time = 0;
  while (ready.size > 0 || head < cooling.length) {
    if (ready.size > 0) {
      const remaining = ready.pop() - 1;
      if (remaining > 0) {
        cooling.push([time + cooldown + 1, remaining]);
      }
      time++;
    } else {
      time = cooling[head][0]; // nothing can run: skip the idle stretch at once
    }
    while (head < cooling.length && cooling[head][0] <= time) {
      ready.push(cooling[head++][1]);
    }
  }
  return time;
}
