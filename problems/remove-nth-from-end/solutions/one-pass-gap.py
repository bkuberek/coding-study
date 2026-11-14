from cs_support import ListNode


def remove_nth_from_end(head: ListNode | None, n: int) -> ListNode | None:
    dummy = ListNode(0, head)
    # `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end,
    # `trail` sits just before the node to remove.
    lead: ListNode | None = dummy
    for _ in range(n + 1):
        lead = lead.next
    trail = dummy
    while lead is not None:
        lead = lead.next
        trail = trail.next
    trail.next = trail.next.next
    return dummy.next
