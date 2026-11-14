import { ListNode } from "#support";

export function reverseList(head: ListNode | null): ListNode | null {
  if (head === null || head.next === null) {
    return head;
  }
  const second = head.next;
  const newHead = reverseList(second);
  // second is now the tail of the reversed rest; head goes after it.
  second.next = head;
  head.next = null;
  return newHead;
}
