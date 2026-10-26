import { ListNode } from "#support";

export function sortList(head: ListNode | null): ListNode | null {
  if (head === null || head.next === null) {
    return head;
  }
  // Starting `fast` one node ahead makes `slow` stop at the end of the left half,
  // so a two-node list splits into one node and one node.
  let slow = head;
  let fast: ListNode | null = head.next;
  while (fast !== null && fast.next !== null) {
    slow = slow.next!;
    fast = fast.next.next;
  }
  const right = slow.next;
  slow.next = null;
  return merge(sortList(head), sortList(right));
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
