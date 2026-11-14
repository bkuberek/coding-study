def check_valid_string(s: str) -> bool:
    opens: list[int] = []  # positions of unmatched "("
    stars: list[int] = []  # positions of unused "*"
    for position, char in enumerate(s):
        if char == "(":
            opens.append(position)
        elif char == "*":
            stars.append(position)
        elif opens:
            opens.pop()  # prefer a real "(" and keep wildcards for later
        elif stars:
            stars.pop()
        else:
            return False
    # Every remaining "(" needs a later "*" to act as its ")".
    while opens and stars:
        if opens.pop() > stars.pop():
            return False
    return not opens
