import { ListNode } from "#support";

export function reverseList(head: ListNode | null): ListNode | null {
  let previous: ListNode | null = null;
  let current = head;
  while (current !== null) {
    // Save the rest of the list before the link that leads to it is redirected.
    const following: ListNode | null = current.next;
    current.next = previous;
    previous = current;
    current = following;
  }
  return previous;
}
