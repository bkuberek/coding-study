import { ListNode } from "#support";

export function sortList(head: ListNode | null): ListNode | null {
  const values: number[] = [];
  for (let node = head; node !== null; node = node.next) {
    values.push(node.val);
  }
  // A typed array sorts numerically without a comparator.
  const sorted = Int32Array.from(values).sort();
  // Write the sorted values back into the same nodes, in list order.
  let index = 0;
  for (let node = head; node !== null; node = node.next) {
    node.val = sorted[index++];
  }
  return head;
}
