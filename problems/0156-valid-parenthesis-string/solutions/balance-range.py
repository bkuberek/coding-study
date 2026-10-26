def check_valid_string(s: str) -> bool:
    # The possible open counts of the prefix are exactly the integers in [lowest, highest].
    lowest = highest = 0
    for char in s:
        if char == "(":
            lowest += 1
            highest += 1
        elif char == ")":
            lowest -= 1
            highest -= 1
        else:
            lowest -= 1  # the wildcard as ")"
            highest += 1  # the wildcard as "("
        if highest < 0:
            return False  # even with every wildcard as "(", too many ")"
        lowest = max(lowest, 0)  # a negative count is not a real choice
    return lowest == 0
