import { ListNode } from "#support";

export function reverseList(head: ListNode | null): ListNode | null {
  const values: number[] = [];
  for (let node = head; node !== null; node = node.next) {
    values.push(node.val);
  }
  // Second pass: the same nodes, in the same order, receive the values from the back.
  for (let node = head; node !== null; node = node.next) {
    node.val = values.pop()!;
  }
  return head;
}
