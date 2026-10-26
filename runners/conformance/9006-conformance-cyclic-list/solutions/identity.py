"""Conformance reference: returns head unchanged, so a cyclic input is a cyclic output."""

from cs_support import ListNode


def echo_list(head: ListNode | None) -> ListNode | None:
    return head
