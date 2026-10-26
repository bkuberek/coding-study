from cs_support import ListNode


def reorder_list(head: ListNode | None) -> None:
    if head is None:
        return
    # 1. Find the end of the front half: for n nodes, `slow` stops at node (n - 1) // 2.
    slow = fast = head
    while fast.next is not None and fast.next.next is not None:
        slow = slow.next
        fast = fast.next.next
    # 2. Cut the list and reverse the back half.
    back = _reverse(slow.next)
    slow.next = None
    # 3. Interleave; the front half is never shorter than the back half.
    front = head
    while back is not None:
        front_next, back_next = front.next, back.next
        front.next = back
        back.next = front_next
        front, back = front_next, back_next


def _reverse(head: ListNode | None) -> ListNode | None:
    previous = None
    current = head
    while current is not None:
        following = current.next
        current.next = previous
        previous, current = current, following
    return previous
