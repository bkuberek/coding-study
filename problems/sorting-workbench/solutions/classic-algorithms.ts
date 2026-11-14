// Four classic sorts, each written the way the statement specifies it, with a meter that counts
// the work of the latest sort. A sort returns a new array and never changes its input.
export class SortingWorkbench {
  private meter: number[] = [];
  private comparisons = 0;

  // Level 1
  insertionSort(values: number[]): number[] {
    const items = [...values];
    let comparisons = 0;
    let moves = 0;
    for (let i = 1; i < items.length; i++) {
      const key = items[i];
      let j = i - 1;
      while (j >= 0) {
        comparisons++;
        if (items[j] <= key) break;
        items[j + 1] = items[j];
        moves++;
        j--;
      }
      items[j + 1] = key;
    }
    this.meter = [comparisons, moves];
    return items;
  }

  report(): number[] {
    return [...this.meter];
  }

  // Level 2
  mergeSortBy(rows: number[][], key: number): number[][] {
    this.comparisons = 0;
    const merged = this.mergeSort(rows, key);
    this.meter = [this.comparisons];
    return merged.map((row) => [...row]);
  }

  private mergeSort(rows: number[][], key: number): number[][] {
    if (rows.length <= 1) return [...rows];
    const middle = rows.length >> 1;
    const left = this.mergeSort(rows.slice(0, middle), key);
    const right = this.mergeSort(rows.slice(middle), key);
    const merged: number[][] = [];
    let i = 0;
    let j = 0;
    while (i < left.length && j < right.length) {
      this.comparisons++;
      if (left[i][key] <= right[j][key]) {
        merged.push(left[i++]);
      } else {
        merged.push(right[j++]);
      }
    }
    while (i < left.length) merged.push(left[i++]);
    while (j < right.length) merged.push(right[j++]);
    return merged;
  }

  // Level 3
  quickSort(values: number[]): number[] {
    const items = [...values];
    let calls = 0;
    let steps = 0;
    const ranges: [number, number][] = [[0, items.length - 1]];
    while (ranges.length > 0) {
      const [low, high] = ranges.pop()!;
      if (high - low < 1) continue;
      const [below, above] = this.partition(items, low, high);
      calls++;
      steps += high - low + 1;
      ranges.push([low, below - 1]);
      ranges.push([above + 1, high]);
    }
    this.meter = [calls, steps];
    return items;
  }

  quickSelect(values: number[], k: number): number {
    const items = [...values];
    const target = k - 1;
    let calls = 0;
    let steps = 0;
    let low = 0;
    let high = items.length - 1;
    while (low < high) {
      const [below, above] = this.partition(items, low, high);
      calls++;
      steps += high - low + 1;
      if (target < below) {
        high = below - 1;
      } else if (target > above) {
        low = above + 1;
      } else {
        break;
      }
    }
    this.meter = [calls, steps];
    return items[target];
  }

  // Afterwards items[low..below-1] < pivot, items[below..above] == pivot and items[above+1..high] > pivot.
  private partition(items: number[], low: number, high: number): [number, number] {
    const pivot = items[low + ((high - low) >> 1)];
    let below = low;
    let i = low;
    let above = high;
    while (i <= above) {
      if (items[i] < pivot) {
        [items[below], items[i]] = [items[i], items[below]];
        below++;
        i++;
      } else if (items[i] > pivot) {
        [items[i], items[above]] = [items[above], items[i]];
        above--;
      } else {
        i++;
      }
    }
    return [below, above];
  }

  // Level 4
  externalSort(values: number[], memory: number, ways: number): number[] {
    let runs: number[][] = [];
    for (let start = 0; start < values.length; start += memory) {
      runs.push(values.slice(start, start + memory).sort((a, b) => a - b));
    }
    const initialRuns = runs.length;
    let passes = 0;
    while (runs.length > 1) {
      const next: number[][] = [];
      for (let start = 0; start < runs.length; start += ways) {
        next.push(this.mergeGroup(runs.slice(start, start + ways)));
      }
      runs = next;
      passes++;
    }
    this.meter = [initialRuns, passes];
    return runs.length > 0 ? runs[0] : [];
  }

  // A binary min-heap of [value, run, position in the run] holds the front value of each run.
  private mergeGroup(group: number[][]): number[] {
    const heap: [number, number, number][] = [];
    const less = (a: [number, number, number], b: [number, number, number]) =>
      a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
    const push = (entry: [number, number, number]) => {
      heap.push(entry);
      let child = heap.length - 1;
      while (child > 0) {
        const parent = (child - 1) >> 1;
        if (!less(heap[child], heap[parent])) break;
        [heap[child], heap[parent]] = [heap[parent], heap[child]];
        child = parent;
      }
    };
    const pop = (): [number, number, number] => {
      const top = heap[0];
      const last = heap.pop()!;
      if (heap.length > 0) {
        heap[0] = last;
        let parent = 0;
        for (;;) {
          const left = 2 * parent + 1;
          const right = left + 1;
          let smallest = parent;
          if (left < heap.length && less(heap[left], heap[smallest])) smallest = left;
          if (right < heap.length && less(heap[right], heap[smallest])) smallest = right;
          if (smallest === parent) break;
          [heap[smallest], heap[parent]] = [heap[parent], heap[smallest]];
          parent = smallest;
        }
      }
      return top;
    };
    group.forEach((run, index) => push([run[0], index, 0]));
    const merged: number[] = [];
    while (heap.length > 0) {
      const [value, index, position] = pop();
      merged.push(value);
      if (position + 1 < group[index].length) {
        push([group[index][position + 1], index, position + 1]);
      }
    }
    return merged;
  }
}
