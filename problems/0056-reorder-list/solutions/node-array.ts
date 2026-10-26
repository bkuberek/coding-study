import { ListNode } from "#support";

export function reorderList(head: ListNode | null): void {
  const nodes: ListNode[] = [];
  for (let node = head; node !== null; node = node.next) {
    nodes.push(node);
  }
  if (nodes.length === 0) {
    return;
  }
  let left = 0;
  let right = nodes.length - 1;
  // Alternate: front node -> back node -> next front node, until the indexes meet.
  while (left < right) {
    nodes[left].next = nodes[right];
    left++;
    if (left === right) {
      break;
    }
    nodes[right].next = nodes[left];
    right--;
  }
  nodes[left].next = null;
}
