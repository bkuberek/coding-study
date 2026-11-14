from cs_support import ListNode


def reorder_list(head: ListNode | None) -> None:
    nodes: list[ListNode] = []
    node = head
    while node is not None:
        nodes.append(node)
        node = node.next
    if not nodes:
        return
    left, right = 0, len(nodes) - 1
    # Alternate: front node -> back node -> next front node, until the indexes meet.
    while left < right:
        nodes[left].next = nodes[right]
        left += 1
        if left == right:
            break
        nodes[right].next = nodes[left]
        right -= 1
    nodes[left].next = None
