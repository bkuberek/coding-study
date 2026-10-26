import { ListNode } from "#support";

export function reverseKGroup(head: ListNode | null, k: number): ListNode | null {
  const values: number[] = [];
  for (let node = head; node !== null; node = node.next) {
    values.push(node.val);
  }
  // Reverse every full chunk in place; a shorter chunk at the end keeps its order.
  for (let start = 0; start + k <= values.length; start += k) {
    for (let left = start, right = start + k - 1; left < right; left++, right--) {
      [values[left], values[right]] = [values[right], values[left]];
    }
  }
  let index = 0;
  for (let node = head; node !== null; node = node.next) {
    node.val = values[index++];
  }
  return head;
}
