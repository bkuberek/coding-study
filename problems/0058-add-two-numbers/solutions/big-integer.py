from cs_support import ListNode


def add_two_numbers(l1: ListNode | None, l2: ListNode | None) -> ListNode | None:
    total = _to_int(l1) + _to_int(l2)
    dummy = ListNode()
    tail = dummy
    while True:
        total, digit = divmod(total, 10)
        tail.next = ListNode(digit)
        tail = tail.next
        if total == 0:
            return dummy.next


def _to_int(head: ListNode | None) -> int:
    digits: list[int] = []
    while head is not None:
        digits.append(head.val)
        head = head.next
    # Horner's rule from the most significant digit. int("".join(...)) would hit Python's
    # 4300-digit limit on string conversion.
    value = 0
    for digit in reversed(digits):
        value = value * 10 + digit
    return value
