from cs_support import ListNode


def reverse_list(head: ListNode | None) -> ListNode | None:
    if head is None or head.next is None:
        return head
    new_head = reverse_list(head.next)
    # head.next is now the tail of the reversed rest; head goes after it.
    head.next.next = head
    head.next = None
    return new_head
