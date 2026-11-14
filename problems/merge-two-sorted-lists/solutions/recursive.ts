import { ListNode } from "#support";

export function mergeTwoLists(list1: ListNode | null, list2: ListNode | null): ListNode | null {
  if (list1 === null) {
    return list2;
  }
  if (list2 === null) {
    return list1;
  }
  // The smaller head starts the merged list; the merge of everything else follows it.
  if (list1.val <= list2.val) {
    list1.next = mergeTwoLists(list1.next, list2);
    return list1;
  }
  list2.next = mergeTwoLists(list1, list2.next);
  return list2;
}
