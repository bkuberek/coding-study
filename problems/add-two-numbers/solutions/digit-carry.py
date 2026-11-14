from cs_support import ListNode


def add_two_numbers(l1: ListNode | None, l2: ListNode | None) -> ListNode | None:
    dummy = ListNode()
    tail = dummy
    carry = 0
    # Keep going while either number has digits left or a carry is still pending.
    while l1 is not None or l2 is not None or carry:
        total = carry
        if l1 is not None:
            total += l1.val
            l1 = l1.next
        if l2 is not None:
            total += l2.val
            l2 = l2.next
        carry, digit = divmod(total, 10)
        tail.next = ListNode(digit)
        tail = tail.next
    return dummy.next
