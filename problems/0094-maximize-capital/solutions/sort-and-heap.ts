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

export function findMaximizedCapital(k: number, w: number, profits: number[], capital: number[]): number {
  const order = profits.map((_, index) => index).sort((a, b) => capital[a] - capital[b]);
  const affordable = new MaxHeap();
  let funds = w;
  let unlocked = 0;
  for (let round = 0; round < k; round++) {
    // Capital only grows, so every project unlocked once stays affordable.
    while (unlocked < order.length && capital[order[unlocked]] <= funds) {
      affordable.push(profits[order[unlocked++]]);
    }
    if (affordable.size === 0) {
      break; // nothing affordable now, and capital cannot grow any more
    }
    funds += affordable.pop();
  }
  return funds;
}
