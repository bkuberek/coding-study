"""Evaluate a filter over groups of users, written in postfix order, with one stack of values.

Each value is a set of user names. The operators are | (union), & (intersection) and
- (difference), and each one is written after the two values it combines.
"""

GROUPS = {
    "admins": {"ana", "bo"},
    "staff": {"bo", "cy", "di", "ed"},
    "oncall": {"cy", "ed", "fay"},
    "away": {"ed"},
}
OPERATIONS = {
    "|": lambda left, right: left | right,
    "&": lambda left, right: left & right,
    "-": lambda left, right: left - right,
}


def show(value: set[str]) -> str:
    return "{" + ", ".join(sorted(value)) + "}"


def evaluate_postfix(tokens: list[str]) -> set[str]:
    values: list[set[str]] = []
    for token in tokens:
        if token in OPERATIONS:
            right = values.pop()  # the newer of the two values is the right operand
            left = values.pop()
            values.append(OPERATIONS[token](left, right))
        else:
            values.append(GROUPS[token])
        print(f"{token:<7} stack, bottom to top: {' '.join(show(value) for value in values)}")
    return values.pop()


tokens = ["staff", "oncall", "&", "away", "-", "admins", "|"]
print("result:", show(evaluate_postfix(tokens)))

staff, oncall, away = GROUPS["staff"], GROUPS["oncall"], GROUPS["away"]
print("the same in Python:", show(((staff & oncall) - away) | GROUPS["admins"]))
print("with the operands of - swapped:", show(away - (staff & oncall)))
