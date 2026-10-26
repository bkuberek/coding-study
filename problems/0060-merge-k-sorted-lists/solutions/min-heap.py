import heapq

from cs_support import ListNode


def merge_k_lists(lists: list[ListNode | None]) -> ListNode | None:
    # Entries are (value, list index, node): the index breaks ties, so heapq never has to
    # compare two ListNode objects (which define no ordering).
    heap = [(head.val, index, head) for index, head in enumerate(lists) if head is not None]
    heapq.heapify(heap)
    dummy = ListNode()
    tail = dummy
    while heap:
        _, index, node = heap[0]
        tail.next = node
        tail = node
        if node.next is not None:
            heapq.heapreplace(heap, (node.next.val, index, node.next))
        else:
            heapq.heappop(heap)
    return dummy.next
