def min_remove_to_make_valid(s: str) -> str:
    # Pass 1, left to right: drop every closer that finds nothing open.
    kept: list[str] = []
    open_count = 0
    for character in s:
        if character == ")":
            if open_count == 0:
                continue
            open_count -= 1
        elif character == "(":
            open_count += 1
        kept.append(character)
    # Pass 2, right to left: drop the last `open_count` openers, which are never closed.
    result: list[str] = []
    for character in reversed(kept):
        if character == "(" and open_count:
            open_count -= 1
            continue
        result.append(character)
    return "".join(reversed(result))
