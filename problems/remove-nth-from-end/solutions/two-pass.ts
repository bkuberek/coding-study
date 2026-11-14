import { ListNode } from "#support";

export function removeNthFromEnd(head: ListNode | null, n: number): ListNode | null {
  let length = 0;
  for (let node = head; node !== null; node = node.next) {
    length++;
  }
  // The dummy node is the predecessor of the head, so removing the head is not special.
  const dummy = new ListNode(0, head);
  let before = dummy;
  for (let step = 0; step < length - n; step++) {
    before = before.next!;
  }
  before.next = before.next!.next;
  return dummy.next;
}
