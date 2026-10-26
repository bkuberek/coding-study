import { ListNode } from "#support";

export function mergeTwoLists(list1: ListNode | null, list2: ListNode | null): ListNode | null {
  const values: number[] = [];
  for (const start of [list1, list2]) {
    for (let node = start; node !== null; node = node.next) {
      values.push(node.val);
    }
  }
  // Without a comparator, sort() would order the numbers as strings.
  values.sort((a, b) => a - b);
  const dummy = new ListNode();
  let tail = dummy;
  for (const value of values) {
    tail.next = new ListNode(value);
    tail = tail.next;
  }
  return dummy.next;
}
