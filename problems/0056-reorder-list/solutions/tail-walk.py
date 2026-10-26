from cs_support import ListNode


def reorder_list(head: ListNode | None) -> None:
    current = head
    # Each round moves the current tail right after `current`; two or fewer nodes from
    # `current` onward are already in their final order.
    while current is not None and current.next is not None and current.next.next is not None:
        before_tail = current
        while before_tail.next.next is not None:
            before_tail = before_tail.next
        tail = before_tail.next
        before_tail.next = None
        tail.next = current.next
        current.next = tail
        current = tail.next
