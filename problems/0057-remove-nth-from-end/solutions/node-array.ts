import { ListNode } from "#support";

export function removeNthFromEnd(head: ListNode | null, n: number): ListNode | null {
  const nodes: ListNode[] = [];
  for (let node = head; node !== null; node = node.next) {
    nodes.push(node);
  }
  const target = nodes.length - n;
  if (target === 0) {
    return nodes[0].next;
  }
  nodes[target - 1].next = nodes[target].next;
  return head;
}
