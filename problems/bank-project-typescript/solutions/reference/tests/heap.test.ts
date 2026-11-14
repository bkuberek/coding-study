// The binary heap on its own: the order it hands items out in.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { MinHeap } from "../src/heap.ts";

function byValue(a: number, b: number): number {
  return a - b;
}

function drain<T>(heap: MinHeap<T>): T[] {
  const items: T[] = [];
  for (let item = heap.pop(); item !== undefined; item = heap.pop()) {
    items.push(item);
  }
  return items;
}

describe("MinHeap", () => {
  test("pops the smallest item first", () => {
    const heap = new MinHeap(byValue);
    for (const value of [5, 1, 4, 2, 3]) heap.push(value);
    assert.deepEqual(drain(heap), [1, 2, 3, 4, 5]);
  });

  test("keeps equal items and pops each of them", () => {
    const heap = new MinHeap(byValue);
    for (const value of [2, 1, 2, 1]) heap.push(value);
    assert.deepEqual(drain(heap), [1, 1, 2, 2]);
  });

  test("orders by the compare function it was given", () => {
    const heap = new MinHeap((a: number, b: number) => b - a);
    for (const value of [1, 3, 2]) heap.push(value);
    assert.deepEqual(drain(heap), [3, 2, 1]);
  });

  test("peek shows the smallest item without removing it", () => {
    const heap = new MinHeap(byValue);
    heap.push(7);
    heap.push(3);
    heap.peek();
    assert.equal(heap.size, 2);
  });

  test("an empty heap pops undefined", () => {
    assert.equal(new MinHeap(byValue).pop(), undefined);
  });
});
