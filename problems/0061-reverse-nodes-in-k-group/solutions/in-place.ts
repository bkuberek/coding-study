import { ListNode } from "#support";

export function reverseKGroup(head: ListNode | null, k: number): ListNode | null {
  const dummy = new ListNode(0, head);
  let before = dummy; // the node just before the next group
  for (;;) {
    let last: ListNode | null = before;
    for (let step = 0; step < k && last !== null; step++) {
      last = last.next;
    }
    if (last === null) {
      return dummy.next; // fewer than k nodes remain: leave them as they are
    }
    const after = last.next;
    // Reverse the group; its first node ends up last, pointing at `after`.
    const first = before.next!;
    let previous = after;
    let current: ListNode | null = first;
    // `after` is null for a group that ends the list, so test `current` for null too.
    while (current !== null && current !== after) {
      const following: ListNode | null = current.next;
      current.next = previous;
      previous = current;
      current = following;
    }
    before.next = last;
    before = first;
  }
}
