interface Scored {
  score: number;
  index: number;
}

// True when a ranks below b: a lower score, or the same score and a higher index.
function ranksBelow(a: Scored, b: Scored): boolean {
  return a.score < b.score || (a.score === b.score && a.index > b.index);
}

// A binary min-heap under ranksBelow, so its root is the weakest document kept.
// TypeScript has no built-in priority queue.
class WeakestFirstHeap {
  readonly items: Scored[] = [];

  get size(): number {
    return this.items.length;
  }

  peek(): Scored {
    return this.items[0];
  }

  push(entry: Scored): void {
    const items = this.items;
    items.push(entry);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (!ranksBelow(items[child], items[parent])) {
        return;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  replaceRoot(entry: Scored): void {
    const items = this.items;
    items[0] = entry;
    let parent = 0;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let weakest = parent;
      if (left < items.length && ranksBelow(items[left], items[weakest])) {
        weakest = left;
      }
      if (right < items.length && ranksBelow(items[right], items[weakest])) {
        weakest = right;
      }
      if (weakest === parent) {
        return;
      }
      [items[parent], items[weakest]] = [items[weakest], items[parent]];
      parent = weakest;
    }
  }
}

function dot(a: number[], b: number[]): number {
  let total = 0;
  for (let j = 0; j < a.length; j += 1) {
    total += a[j] * b[j];
  }
  return total;
}

export function topKCosine(query: number[], documents: number[][], k: number): number[] {
  const queryNorm = Math.sqrt(dot(query, query));
  if (queryNorm === 0) {
    return [];
  }
  const heap = new WeakestFirstHeap();
  documents.forEach((document, index) => {
    const documentNorm = Math.sqrt(dot(document, document));
    if (documentNorm === 0) {
      return;
    }
    const entry = { score: dot(query, document) / (queryNorm * documentNorm), index };
    if (heap.size < k) {
      heap.push(entry);
    } else if (ranksBelow(heap.peek(), entry)) {
      heap.replaceRoot(entry);
    }
  });
  return heap.items.sort((a, b) => b.score - a.score || a.index - b.index).map((entry) => entry.index);
}
