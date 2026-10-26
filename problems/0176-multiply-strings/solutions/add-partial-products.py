def _times_digit(digits: list[int], factor: int) -> list[int]:
    """Little-endian digits of (digits * factor)."""
    product, carry = [], 0
    for digit in digits:
        carry, written = divmod(digit * factor + carry, 10)
        product.append(written)
    if carry:
        product.append(carry)
    return product


def _add(left: list[int], right: list[int]) -> list[int]:
    """Little-endian digits of left + right."""
    total, carry = [], 0
    for position in range(max(len(left), len(right))):
        a = left[position] if position < len(left) else 0
        b = right[position] if position < len(right) else 0
        carry, written = divmod(a + b + carry, 10)
        total.append(written)
    if carry:
        total.append(carry)
    return total


def multiply(num1: str, num2: str) -> str:
    if num1 == "0" or num2 == "0":
        return "0"
    first = [int(ch) for ch in reversed(num1)]
    total: list[int] = []
    # School method: one row per digit of num2, shifted by its position.
    for shift, ch in enumerate(reversed(num2)):
        row = [0] * shift + _times_digit(first, int(ch))
        total = _add(total, row)
    return "".join(str(digit) for digit in reversed(total))
