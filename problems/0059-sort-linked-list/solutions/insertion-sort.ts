import { ListNode } from "#support";

export function sortList(head: ListNode | null): ListNode | null {
  const dummy = new ListNode(); // head of the sorted prefix
  let node = head;
  while (node !== null) {
    const following: ListNode | null = node.next;
    // Find the last sorted node whose value is smaller, and insert after it.
    let spot = dummy;
    while (spot.next !== null && spot.next.val < node.val) {
      spot = spot.next;
    }
    node.next = spot.next;
    spot.next = node;
    node = following;
  }
  return dummy.next;
}
