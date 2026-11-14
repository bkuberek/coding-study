"""Conformance reference: returns head itself, which no_alias_with rejects."""

from cs_support import ListNode


def copy_list(head: ListNode | None) -> ListNode | None:
    return head
