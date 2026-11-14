from cs_support import ListNode


def reverse_k_group(head: ListNode | None, k: int) -> ListNode | None:
    dummy = ListNode()
    tail = dummy
    node = head
    while True:
        # Take up to k nodes; popping them off the stack yields the group reversed.
        stack: list[ListNode] = []
        probe = node
        while probe is not None and len(stack) < k:
            stack.append(probe)
            probe = probe.next
        if len(stack) < k:
            tail.next = node  # a short tail keeps its order
            return dummy.next
        while stack:
            tail.next = stack.pop()
            tail = tail.next
        node = probe
