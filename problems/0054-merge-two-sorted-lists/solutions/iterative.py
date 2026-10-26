from cs_support import ListNode


def merge_two_lists(list1: ListNode | None, list2: ListNode | None) -> ListNode | None:
    # The dummy node gives the merged list a fixed place to start, so the first splice
    # needs no special case.
    dummy = ListNode()
    tail = dummy
    while list1 is not None and list2 is not None:
        if list1.val <= list2.val:
            tail.next, list1 = list1, list1.next
        else:
            tail.next, list2 = list2, list2.next
        tail = tail.next
    # At most one list has nodes left, and they are already sorted: link them as a block.
    tail.next = list1 if list1 is not None else list2
    return dummy.next
