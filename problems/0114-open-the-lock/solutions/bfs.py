from collections import deque

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
    # Dead ends behave like settings that were already visited: the search never enters them.
    seen = set(deadends)
    if START in seen:
        return -1
    seen.add(START)
    queue = deque([(START, 0)])
    while queue:
        setting, moves = queue.popleft()
        if setting == target:
            return moves
        for following in _turns(setting):
            if following not in seen:
                seen.add(following)
                queue.append((following, moves + 1))
    return -1
