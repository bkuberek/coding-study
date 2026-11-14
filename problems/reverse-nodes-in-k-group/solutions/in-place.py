from cs_support import ListNode


def reverse_k_group(head: ListNode | None, k: int) -> ListNode | None:
    dummy = ListNode(0, head)
    before = dummy  # the node just before the next group
    while True:
        last = before
        for _ in range(k):
            last = last.next
            if last is None:
                return dummy.next  # fewer than k nodes remain: leave them as they are
        after = last.next
        # Reverse the group; its first node ends up last, pointing at `after`.
        first = before.next
        previous, current = after, first
        while current is not after:
            following = current.next
            current.next = previous
            previous, current = current, following
        before.next = last
        before = first
