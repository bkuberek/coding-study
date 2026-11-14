from cs_support import ListNode


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    if not lists:
        return None
    # Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
    # every node takes part in one merge per round, and there are ceil(log2 k) rounds.
    heads = list(lists)
    while len(heads) > 1:
        heads = [
            _merge(heads[index], heads[index + 1] if index + 1 < len(heads) else None)
            for index in range(0, len(heads), 2)
        ]
    return heads[0]


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
