import { ListNode } from "#support";

export function mergeKLists(lists: (ListNode | null)[]): ListNode | null {
  if (lists.length === 0) {
    return null;
  }
  // Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
  // every node takes part in one merge per round, and there are ceil(log2 k) rounds.
  let heads = lists;
  while (heads.length > 1) {
    const next: (ListNode | null)[] = [];
    for (let index = 0; index < heads.length; index += 2) {
      next.push(merge(heads[index], index + 1 < heads.length ? heads[index + 1] : null));
    }
    heads = next;
  }
  return heads[0];
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
