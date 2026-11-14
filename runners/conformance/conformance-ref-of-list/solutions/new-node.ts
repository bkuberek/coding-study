import { ListNode } from "#support";

export function pickNode(
  head: ListNode | null,
  node: ListNode | null,
): ListNode | null {
  return node === null ? null : new ListNode(node.val);
}
