import { ListNode } from "#support";

export function addTwoNumbers(l1: ListNode | null, l2: ListNode | null): ListNode | null {
  const dummy = new ListNode();
  let tail = dummy;
  let first = l1;
  let second = l2;
  let carry = 0;
  // Keep going while either number has digits left or a carry is still pending.
  while (first !== null || second !== null || carry > 0) {
    let total = carry;
    if (first !== null) {
      total += first.val;
      first = first.next;
    }
    if (second !== null) {
      total += second.val;
      second = second.next;
    }
    carry = Math.floor(total / 10);
    tail.next = new ListNode(total % 10);
    tail = tail.next;
  }
  return dummy.next;
}
