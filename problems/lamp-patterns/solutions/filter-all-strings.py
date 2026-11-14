def lamp_patterns(n: int) -> list[str]:
    result: list[str] = []
    for number in range(1 << n):
        # Counting up writes the strings in increasing order; the bits are the lamps.
        pattern = format(number, f"0{n}b")
        if "11" not in pattern:
            result.append(pattern)
    return result
