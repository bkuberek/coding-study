def multiply(num1: str, num2: str) -> str:
    if num1 == "0" or num2 == "0":
        return "0"
    first = [int(ch) for ch in num1]
    second = [int(ch) for ch in num2]
    # digits[k] is result digit k counted from the left; the product has at most m + n digits.
    digits = [0] * (len(first) + len(second))
    for i in range(len(first) - 1, -1, -1):
        carry = 0
        for j in range(len(second) - 1, -1, -1):
            carry, digits[i + j + 1] = divmod(digits[i + j + 1] + first[i] * second[j] + carry, 10)
        digits[i] += carry
    start = 0 if digits[0] != 0 else 1  # at most one leading zero
    return "".join(map(str, digits[start:]))
