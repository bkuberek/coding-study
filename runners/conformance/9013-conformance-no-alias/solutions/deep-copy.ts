import { ListNode } from "#support";

export function copyList(head: ListNode | null): ListNode | null {
  const sentinel = new ListNode();
  let tail = sentinel;
  for (let node = head; node !== null; node = node.next) {
    tail.next = new ListNode(node.val);
    tail = tail.next;
  }
  return sentinel.next;
}
