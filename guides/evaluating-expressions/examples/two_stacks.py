"""Evaluate an ordinary (infix) filter in one pass, with a stack of values and a stack of operators.

& binds tighter than | and -, which share one level and group from left to right, like * over +
and - in arithmetic. Parentheses override both rules.
"""

import re

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
PRECEDENCE = {"|": 1, "-": 1, "&": 2}


def show(value: set[str]) -> str:
    return "{" + ", ".join(sorted(value)) + "}"


def evaluate(text: str, trace: bool = False, left_to_right: bool = True) -> set[str]:
    values: list[set[str]] = []
    operators: list[str] = []

    def apply_top() -> None:
        operator = operators.pop()
        right = values.pop()
        left = values.pop()
        values.append(OPERATIONS[operator](left, right))

    def top_goes_first(new: str) -> bool:
        """Whether the operator on top must apply before `new` joins the stack."""
        if not operators or operators[-1] == "(":
            return False
        waiting = PRECEDENCE[operators[-1]]
        return waiting >= PRECEDENCE[new] if left_to_right else waiting > PRECEDENCE[new]

    for token in re.findall(r"[a-z]+|[()|&-]", text):
        if token == "(":
            operators.append(token)  # a wall: nothing below it applies until its ")" arrives
        elif token == ")":
            while operators[-1] != "(":
                apply_top()
            operators.pop()  # the "(" itself
        elif token in OPERATIONS:
            while top_goes_first(token):
                apply_top()
            operators.append(token)
        else:
            values.append(GROUPS[token])
        if trace:
            shown = " ".join(show(value) for value in values)
            print(f"{token:<7} values: {shown:<40} operators: {' '.join(operators) or '(none)'}")
    while operators:
        apply_top()
    return values.pop()


print("result:", show(evaluate("admins | staff & oncall - away", trace=True)))
admins, staff, oncall, away = (GROUPS[name] for name in ("admins", "staff", "oncall", "away"))
print("the same in Python:", show((admins | (staff & oncall)) - away))

for text in ("admins | staff & oncall", "(admins | staff) & oncall"):
    print(f"{text:<26} = {show(evaluate(text))}")
print("staff - oncall - away, left to right:", show(evaluate("staff - oncall - away")))
print(
    "staff - oncall - away, right to left:",
    show(evaluate("staff - oncall - away", left_to_right=False)),
)
