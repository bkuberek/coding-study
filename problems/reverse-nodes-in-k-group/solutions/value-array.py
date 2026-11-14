from cs_support import ListNode


def reverse_k_group(head: ListNode | None, k: int) -> ListNode | None:
    values: list[int] = []
    node = head
    while node is not None:
        values.append(node.val)
        node = node.next
    # Reverse every full chunk; a shorter chunk at the end keeps its order.
    for start in range(0, len(values) - k + 1, k):
        values[start : start + k] = values[start : start + k][::-1]
    node = head
    for value in values:
        node.val = value
        node = node.next
    return head
