import { ListNode } from "#support";

export function removeNthFromEnd(head: ListNode | null, n: number): ListNode | null {
  const dummy = new ListNode(0, head);
  // `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end,
  // `trail` sits just before the node to remove.
  let lead: ListNode | null = dummy;
  for (let step = 0; step <= n; step++) {
    lead = lead!.next;
  }
  let trail = dummy;
  while (lead !== null) {
    lead = lead.next;
    trail = trail.next!;
  }
  trail.next = trail.next!.next;
  return dummy.next;
}
