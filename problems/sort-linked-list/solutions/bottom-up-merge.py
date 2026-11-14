from cs_support import ListNode


def sort_list(head: ListNode | None) -> ListNode | None:
    length = 0
    node = head
    while node is not None:
        length += 1
        node = node.next
    dummy = ListNode(0, head)
    width = 1
    # After the pass with width w, the list is a sequence of sorted runs of length 2w.
    while width < length:
        tail = dummy
        rest = dummy.next
        while rest is not None:
            left = rest
            right = _cut_after(left, width)
            rest = _cut_after(right, width)
            tail = _merge_onto(tail, left, right)
        width *= 2
    return dummy.next


def _cut_after(head: ListNode | None, size: int) -> ListNode | None:
    """Detach the first `size` nodes from the rest and return the rest's head."""
    for _ in range(size - 1):
        if head is None:
            return None
        head = head.next
    if head is None:
        return None
    rest = head.next
    head.next = None
    return rest


def _merge_onto(tail: ListNode, left: ListNode | None, right: ListNode | None) -> ListNode:
    """Append the merge of two sorted runs after `tail` and return the new tail."""
    while left is not None and right is not None:
        if left.val <= right.val:
            tail.next, left = left, left.next
        else:
            tail.next, right = right, right.next
        tail = tail.next
    tail.next = left if left is not None else right
    while tail.next is not None:
        tail = tail.next
    return tail
