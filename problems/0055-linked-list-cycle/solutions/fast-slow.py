from cs_support import ListNode


def has_cycle(head: ListNode | None) -> bool:
    slow = fast = head
    # The fast pointer reaches the end first when there is no loop; inside a loop it gains
    # one node per step on the slow pointer and must land on it.
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False
