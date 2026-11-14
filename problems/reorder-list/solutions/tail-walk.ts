import { ListNode } from "#support";

export function reorderList(head: ListNode | null): void {
  let current = head;
  // Each round moves the current tail right after `current`; two or fewer nodes from
  // `current` onward are already in their final order.
  while (current !== null && current.next !== null && current.next.next !== null) {
    let beforeTail: ListNode = current;
    while (beforeTail.next!.next !== null) {
      beforeTail = beforeTail.next!;
    }
    const tail = beforeTail.next!;
    beforeTail.next = null;
    tail.next = current.next;
    current.next = tail;
    current = tail.next;
  }
}
