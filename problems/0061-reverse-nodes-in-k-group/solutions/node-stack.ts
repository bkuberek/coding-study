import { ListNode } from "#support";

export function reverseKGroup(head: ListNode | null, k: number): ListNode | null {
  const dummy = new ListNode();
  let tail = dummy;
  let node = head;
  for (;;) {
    // Take up to k nodes; popping them off the stack yields the group reversed.
    const stack: ListNode[] = [];
    let probe = node;
    while (probe !== null && stack.length < k) {
      stack.push(probe);
      probe = probe.next;
    }
    if (stack.length < k) {
      tail.next = node; // a short tail keeps its order
      return dummy.next;
    }
    while (stack.length > 0) {
      tail.next = stack.pop()!;
      tail = tail.next;
    }
    node = probe;
  }
}
