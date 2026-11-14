// A binary min-heap. JavaScript has no priority queue, so the project carries its own.

/** Negative when `a` comes before `b`, positive when after, zero when either may: as for `sort`. */
export type Compare<T> = (a: T, b: T) => number;

/** Hands items out smallest first, by a compare function. Push and pop take O(log n). */
export class MinHeap<T> {
  readonly #items: T[] = [];
  readonly #compare: Compare<T>;

  constructor(compare: Compare<T>) {
    this.#compare = compare;
  }

  get size(): number {
    return this.#items.length;
  }

  /** The smallest item, left in place; undefined when the heap is empty. */
  peek(): T | undefined {
    return this.#items[0];
  }

  push(item: T): void {
    this.#items.push(item);
    this.#siftUp(this.#items.length - 1);
  }

  /** Removes and returns the smallest item; undefined when the heap is empty. */
  pop(): T | undefined {
    const top = this.#items[0];
    const last = this.#items.pop();
    if (this.#items.length > 0 && last !== undefined) {
      this.#items[0] = last;
      this.#siftDown(0);
    }
    return top;
  }

  #siftUp(index: number): void {
    let child = index;
    while (child > 0) {
      const parent = Math.floor((child - 1) / 2);
      if (!this.#before(child, parent)) return;
      this.#swap(child, parent);
      child = parent;
    }
  }

  #siftDown(index: number): void {
    let parent = index;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let first = parent;
      if (left < this.#items.length && this.#before(left, first)) first = left;
      if (right < this.#items.length && this.#before(right, first)) first = right;
      if (first === parent) return;
      this.#swap(parent, first);
      parent = first;
    }
  }

  #before(i: number, j: number): boolean {
    return this.#compare(this.#items[i], this.#items[j]) < 0;
  }

  #swap(i: number, j: number): void {
    [this.#items[i], this.#items[j]] = [this.#items[j], this.#items[i]];
  }
}
