def lamp_patterns(n: int) -> list[str]:
    result: list[str] = []
    lamps: list[str] = []

    def extend() -> None:
        if len(lamps) == n:
            result.append("".join(lamps))
            return
        lamps.append("0")  # choose: off
        extend()  # explore
        lamps.pop()  # undo
        # Prune: a lamp may be on only when its left neighbour is off (or missing).
        if not lamps or lamps[-1] == "0":
            lamps.append("1")
            extend()
            lamps.pop()

    extend()
    return result
