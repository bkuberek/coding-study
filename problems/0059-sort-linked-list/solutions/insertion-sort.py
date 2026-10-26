from cs_support import ListNode


def sort_list(head: ListNode | None) -> ListNode | None:
    dummy = ListNode()  # head of the sorted prefix
    node = head
    while node is not None:
        following = node.next
        # Find the last sorted node whose value is smaller, and insert after it.
        spot = dummy
        while spot.next is not None and spot.next.val < node.val:
            spot = spot.next
        node.next = spot.next
        spot.next = node
        node = following
    return dummy.next
