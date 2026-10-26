import { ListNode } from "#support";

export function sortList(head: ListNode | null): ListNode | null {
  let length = 0;
  for (let node = head; node !== null; node = node.next) {
    length++;
  }
  const dummy = new ListNode(0, head);
  // After the pass with width w, the list is a sequence of sorted runs of length 2w.
  for (let width = 1; width < length; width *= 2) {
    let tail = dummy;
    let rest = dummy.next;
    while (rest !== null) {
      const left = rest;
      const right = cutAfter(left, width);
      rest = cutAfter(right, width);
      tail = mergeOnto(tail, left, right);
    }
  }
  return dummy.next;
}

/** Detach the first `size` nodes from the rest and return the rest's head. */
function cutAfter(head: ListNode | null, size: number): ListNode | null {
  let node = head;
  for (let step = 1; step < size && node !== null; step++) {
    node = node.next;
  }
  if (node === null) {
    return null;
  }
  const rest = node.next;
  node.next = null;
  return rest;
}

/** Append the merge of two sorted runs after `tail` and return the new tail. */
function mergeOnto(tail: ListNode, left: ListNode | null, right: ListNode | null): ListNode {
  let last = tail;
  while (left !== null && right !== null) {
    if (left.val <= right.val) {
      last.next = left;
      left = left.next;
    } else {
      last.next = right;
      right = right.next;
    }
    last = last.next;
  }
  last.next = left ?? right;
  while (last.next !== null) {
    last = last.next;
  }
  return last;
}
