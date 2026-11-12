GOOD, BAD = 0, 1


def first_bad_commit(statuses: list[int]) -> list[int]:
    last_good = -1
    for position, status in enumerate(statuses):
        if status == GOOD:
            last_good = position
        elif status == BAD:
            return [last_good + 1, position]
    raise ValueError("the history has no bad commit")
