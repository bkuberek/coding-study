from cs_support import ListNode


def merge_two_lists(list1: ListNode | None, list2: ListNode | None) -> ListNode | None:
    values: list[int] = []
    for node in (list1, list2):
        while node is not None:
            values.append(node.val)
            node = node.next
    values.sort()
    dummy = ListNode()
    tail = dummy
    for value in values:
        tail.next = ListNode(value)
        tail = tail.next
    return dummy.next
