from cs_support import ListNode


def sort_list(head: ListNode | None) -> ListNode | None:
    if head is None or head.next is None:
        return head
    # Starting `fast` one node ahead makes `slow` stop at the end of the left half,
    # so a two-node list splits into one node and one node.
    slow, fast = head, head.next
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
    right = slow.next
    slow.next = None
    return _merge(sort_list(head), sort_list(right))


def _merge(left: ListNode | None, right: ListNode | None) -> ListNode | None:
    dummy = ListNode()
    tail = dummy
    while left is not None and right is not None:
        if left.val <= right.val:
            tail.next, left = left, left.next
        else:
            tail.next, right = right, right.next
        tail = tail.next
    tail.next = left if left is not None else right
    return dummy.next
