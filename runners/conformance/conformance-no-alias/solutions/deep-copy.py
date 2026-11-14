"""Conformance reference: builds new nodes with the same values."""

from cs_support import ListNode


def copy_list(head: ListNode | None) -> ListNode | None:
    sentinel = ListNode()
    tail = sentinel
    node = head
    while node is not None:
        tail.next = ListNode(node.val)
        tail = tail.next
        node = node.next
    return sentinel.next
