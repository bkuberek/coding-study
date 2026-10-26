def check_valid_string(s: str) -> bool:
    # possible holds every open count some choice of wildcards can produce for the prefix.
    possible = {0}
    for char in s:
        following: set[int] = set()
        for open_count in possible:
            if char in "(*":
                following.add(open_count + 1)
            if char in ")*" and open_count > 0:
                following.add(open_count - 1)
            if char == "*":
                following.add(open_count)
        possible = following
        if not possible:
            return False
    return 0 in possible
