START = "0000"


def _turns(setting: str) -> list[str]:
    """The eight settings one move away: each wheel up or down by one, wrapping around."""
    result = []
    for wheel in range(4):
        digit = int(setting[wheel])
        for turn in (1, 9):
            result.append(setting[:wheel] + str((digit + turn) % 10) + setting[wheel + 1 :])
    return result


def open_lock(deadends: list[str], target: str) -> int:
    blocked = set(deadends)
    if START in blocked:
        return -1
    if target == START:
        return 0
    # Two frontiers grow toward each other; moves counts the levels expanded so far.
    near, far = {START}, {target}
    seen = {START, target}
    moves = 0
    while near and far:
        if len(near) > len(far):
            near, far = far, near  # always expand the smaller frontier
        moves += 1
        following_level = set()
        for setting in near:
            for following in _turns(setting):
                if following in far:
                    return moves
                if following not in seen and following not in blocked:
                    seen.add(following)
                    following_level.add(following)
        near = following_level
    return -1
