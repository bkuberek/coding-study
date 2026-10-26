def remove_k_digits(num: str, k: int) -> str:
    # The digits kept so far; they never decrease from bottom to top.
    kept: list[str] = []
    remaining = k
    for digit in num:
        while remaining and kept and kept[-1] > digit:
            kept.pop()
            remaining -= 1
        kept.append(digit)
    # The kept digits never decrease, so leftover deletions are cheapest at the end.
    kept = kept[: len(kept) - remaining]
    return "".join(kept).lstrip("0") or "0"
