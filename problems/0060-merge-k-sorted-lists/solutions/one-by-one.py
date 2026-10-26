from cs_support import ListNode


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    merged: ListNode | None = None
    for head in lists:
        merged = _merge(merged, head)
    return merged


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
