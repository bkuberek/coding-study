from cs_support import ListNode


def reverse_list(head: ListNode | None) -> ListNode | None:
    values: list[int] = []
    node = head
    while node is not None:
        values.append(node.val)
        node = node.next
    # Second pass: the same nodes, in the same order, receive the values from the back.
    node = head
    while node is not None:
        node.val = values.pop()
        node = node.next
    return head
