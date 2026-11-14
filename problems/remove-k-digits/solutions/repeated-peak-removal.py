def remove_k_digits(num: str, k: int) -> str:
    digits = list(num)
    for _ in range(k):
        # The first digit larger than its successor, or the last digit if none is.
        peak = 0
        while peak + 1 < len(digits) and digits[peak] <= digits[peak + 1]:
            peak += 1
        del digits[peak]
    return "".join(digits).lstrip("0") or "0"
