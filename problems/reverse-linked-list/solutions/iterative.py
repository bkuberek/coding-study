from cs_support import ListNode


def reverse_list(head: ListNode | None) -> ListNode | None:
    previous: ListNode | None = None
    current = head
    while current is not None:
        # Save the rest of the list before the link that leads to it is redirected.
        following = current.next
        current.next = previous
        previous, current = current, following
    return previous
