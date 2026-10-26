from cs_support import ListNode


def remove_nth_from_end(head: ListNode | None, n: int) -> ListNode | None:
    nodes: list[ListNode] = []
    node = head
    while node is not None:
        nodes.append(node)
        node = node.next
    target = len(nodes) - n
    if target == 0:
        return nodes[0].next
    nodes[target - 1].next = nodes[target].next
    return head
