from collections import Counter


def least_interval(tasks: list[str], cooldown: int) -> int:
    counts = Counter(tasks).values()
    top = max(counts)
    tied = sum(1 for count in counts if count == top)
    # top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
    # tied most frequent tasks. With enough other tasks, no slot idles and the answer is
    # simply the number of tasks.
    return max(len(tasks), (top - 1) * (cooldown + 1) + tied)
