"""Conformance reference: returns a new node, which is not a node of head."""

from cs_support import ListNode


def pick_node(head: ListNode | None, node: ListNode | None) -> ListNode | None:
    return None if node is None else ListNode(node.val)
