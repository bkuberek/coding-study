import { ListNode } from "#support";

export function reorderList(head: ListNode | null): void {
  if (head === null) {
    return;
  }
  // 1. Find the end of the front half: for n nodes, `slow` stops at node (n - 1) / 2.
  let slow = head;
  let fast = head;
  while (fast.next !== null && fast.next.next !== null) {
    slow = slow.next!;
    fast = fast.next.next;
  }
  // 2. Cut the list and reverse the back half.
  let back = reverse(slow.next);
  slow.next = null;
  // 3. Interleave; the front half is never shorter than the back half, so `front` only
  // runs out together with `back` (even length) or one node after it (odd length).
  let front: ListNode | null = head;
  while (front !== null && back !== null) {
    const frontNext: ListNode | null = front.next;
    const backNext: ListNode | null = back.next;
    front.next = back;
    back.next = frontNext;
    front = frontNext;
    back = backNext;
  }
}

function reverse(head: ListNode | null): ListNode | null {
  let previous: ListNode | null = null;
  let current = head;
  while (current !== null) {
    const following: ListNode | null = current.next;
    current.next = previous;
    previous = current;
    current = following;
  }
  return previous;
}
