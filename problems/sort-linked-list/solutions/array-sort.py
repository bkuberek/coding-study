from cs_support import ListNode


def sort_list(head: ListNode | None) -> ListNode | None:
    values: list[int] = []
    node = head
    while node is not None:
        values.append(node.val)
        node = node.next
    values.sort()
    # Write the sorted values back into the same nodes, in list order.
    node = head
    for value in values:
        node.val = value
        node = node.next
    return head
