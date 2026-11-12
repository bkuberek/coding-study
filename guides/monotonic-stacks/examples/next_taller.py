"""For each person in a line, the first person in front who blocks the view, with a monotonic stack.

Everyone faces right and looks over the people in front of them. The first one who is strictly
taller blocks the view. The stack holds the people whose blocker has not turned up yet.
"""

from collections.abc import Callable

HEIGHTS = [160, 172, 165, 158, 165, 180, 170]


def taller(new: int, waiting: int) -> bool:
    return new > waiting


def first_in_front(
    heights: list[int], beats: Callable[[int, int], bool] = taller, show: bool = False
) -> tuple[list[int | None], int]:
    """For each position, the first position in front whose height beats it, and the stack work."""
    answer: list[int | None] = [None] * len(heights)
    waiting: list[int] = []  # positions whose answer is unknown, the most recent on top
    operations = 0
    for position, height in enumerate(heights):
        answered = []
        while waiting and beats(height, heights[waiting[-1]]):
            earlier = waiting.pop()
            answer[earlier] = position
            answered.append(earlier)
        waiting.append(position)
        operations += len(answered) + 1
        if show:
            stack = " ".join(f"#{p}:{heights[p]}" for p in waiting)
            print(f"#{position} {height} cm answers {answered!s:<9} stack, bottom to top: {stack}")
    return answer, operations


answer, _ = first_in_front(HEIGHTS, show=True)
blockers = ["nobody" if a is None else f"#{a}" for a in answer]
print("blocked by:", ", ".join(f"#{p}->{blocker}" for p, blocker in enumerate(blockers)))
print("if equal heights blocked too:", first_in_front(HEIGHTS, lambda new, old: new >= old)[0])
print("first shorter in front:     ", first_in_front(HEIGHTS, lambda new, old: new < old)[0])


def first_taller_by_scanning(heights: list[int]) -> tuple[list[int | None], int]:
    answer: list[int | None] = [None] * len(heights)
    comparisons = 0
    for position, height in enumerate(heights):
        for ahead in range(position + 1, len(heights)):
            comparisons += 1
            if heights[ahead] > height:
                answer[position] = ahead
                break
    return answer, comparisons


line = [*range(2_000, 0, -1), 2_001]  # a long run of ever shorter people, then a giant
by_stack, operations = first_in_front(line)
by_scan, comparisons = first_taller_by_scanning(line)
print(f"{len(line):,} people: same answers: {by_stack == by_scan}")
print(f"scanning ahead: {comparisons:,} comparisons; the stack: {operations:,} pushes and pops")
