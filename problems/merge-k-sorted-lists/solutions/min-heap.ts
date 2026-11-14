import { ListNode } from "#support";

// A binary min-heap of list nodes ordered by value: TypeScript has no built-in priority queue.
class NodeHeap {
  private readonly items: ListNode[] = [];

  get size(): number {
    return this.items.length;
  }

  push(node: ListNode): void {
    const items = this.items;
    items.push(node);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent].val <= items[child].val) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): ListNode {
    const items = this.items;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      this.siftDown(0);
    }
    return top;
  }

  private siftDown(start: number): void {
    const items = this.items;
    let parent = start;
    for (;;) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let smallest = parent;
      if (left < items.length && items[left].val < items[smallest].val) {
        smallest = left;
      }
      if (right < items.length && items[right].val < items[smallest].val) {
        smallest = right;
      }
      if (smallest === parent) {
        return;
      }
      [items[parent], items[smallest]] = [items[smallest], items[parent]];
      parent = smallest;
    }
  }
}

export function mergeKLists(lists: (ListNode | null)[]): ListNode | null {
  const heap = new NodeHeap();
  for (const head of lists) {
    if (head !== null) {
      heap.push(head);
    }
  }
  const dummy = new ListNode();
  let tail = dummy;
  while (heap.size > 0) {
    const node = heap.pop();
    tail.next = node;
    tail = node;
    if (node.next !== null) {
      heap.push(node.next);
    }
  }
  return dummy.next;
}
