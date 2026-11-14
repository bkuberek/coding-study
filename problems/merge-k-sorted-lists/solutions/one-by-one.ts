import { ListNode } from "#support";

export function mergeKLists(lists: (ListNode | null)[]): ListNode | null {
  let merged: ListNode | null = null;
  for (const head of lists) {
    merged = merge(merged, head);
  }
  return merged;
}

function merge(left: ListNode | null, right: ListNode | null): ListNode | null {
  const dummy = new ListNode();
  let tail = dummy;
  while (left !== null && right !== null) {
    if (left.val <= right.val) {
      tail.next = left;
      left = left.next;
    } else {
      tail.next = right;
      right = right.next;
    }
    tail = tail.next;
  }
  tail.next = left ?? right;
  return dummy.next;
}
