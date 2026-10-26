import { ListNode } from "#support";

export function hasCycle(head: ListNode | null): boolean {
  // A Set compares objects by reference, so equal values in different nodes stay distinct.
  const visited = new Set<ListNode>();
  for (let node = head; node !== null; node = node.next) {
    if (visited.has(node)) {
      return true;
    }
    visited.add(node);
  }
  return false;
}
