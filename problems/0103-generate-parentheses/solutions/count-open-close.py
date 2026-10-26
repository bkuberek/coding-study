def generate_parenthesis(n: int) -> list[str]:
    result: list[str] = []
    brackets: list[str] = []

    def extend(opened: int, closed: int) -> None:
        if closed == n:
            result.append("".join(brackets))
            return
        if opened < n:
            brackets.append("(")
            extend(opened + 1, closed)
            brackets.pop()
        # A ")" is allowed only while it has an unmatched "(" to close.
        if closed < opened:
            brackets.append(")")
            extend(opened, closed + 1)
            brackets.pop()

    extend(0, 0)
    return result
