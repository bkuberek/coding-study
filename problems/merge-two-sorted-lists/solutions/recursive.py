from cs_support import ListNode


def merge_two_lists(list1: ListNode | None, list2: ListNode | None) -> ListNode | None:
    if list1 is None:
        return list2
    if list2 is None:
        return list1
    # The smaller head starts the merged list; the merge of everything else follows it.
    if list1.val <= list2.val:
        list1.next = merge_two_lists(list1.next, list2)
        return list1
    list2.next = merge_two_lists(list1, list2.next)
    return list2
