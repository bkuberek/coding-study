from cs_support import ListNode


def remove_nth_from_end(head: ListNode | None, n: int) -> ListNode | None:
    length = 0
    node = head
    while node is not None:
        length += 1
        node = node.next
    # The dummy node is the predecessor of the head, so removing the head is not special.
    dummy = ListNode(0, head)
    before = dummy
    for _ in range(length - n):
        before = before.next
    before.next = before.next.next
    return dummy.next
