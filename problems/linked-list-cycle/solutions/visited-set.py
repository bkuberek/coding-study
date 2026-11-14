from cs_support import ListNode


def has_cycle(head: ListNode | None) -> bool:
    # Nodes hash by identity, so equal values in different nodes stay distinct.
    visited: set[ListNode] = set()
    node = head
    while node is not None:
        if node in visited:
            return True
        visited.add(node)
        node = node.next
    return False
