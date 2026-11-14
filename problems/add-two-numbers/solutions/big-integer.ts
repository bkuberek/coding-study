import { ListNode } from "#support";

export function addTwoNumbers(l1: ListNode | null, l2: ListNode | null): ListNode | null {
  let total = toBigInt(l1) + toBigInt(l2);
  const dummy = new ListNode();
  let tail = dummy;
  // Least significant digit first, like the input lists; a zero sum still gets its one node.
  do {
    tail.next = new ListNode(Number(total % 10n));
    tail = tail.next;
    total /= 10n;
  } while (total > 0n);
  return dummy.next;
}

function toBigInt(head: ListNode | null): bigint {
  const digits: number[] = [];
  for (let node = head; node !== null; node = node.next) {
    digits.push(node.val);
  }
  // Horner's rule from the most significant digit. BigInt("...") would parse the whole decimal
  // string with V8's subquadratic algorithm, which is not the method this approach describes.
  let value = 0n;
  for (let index = digits.length - 1; index >= 0; index--) {
    value = value * 10n + BigInt(digits[index]);
  }
  return value;
}
