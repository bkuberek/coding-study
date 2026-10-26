from collections import Counter


def is_n_straight_hand(hand: list[int], group_size: int) -> bool:
    if len(hand) % group_size != 0:
        return False
    counts = Counter(hand)
    for value in sorted(counts):
        starting = counts[value]
        if starting == 0:
            continue
        # Every card left at the smallest remaining value starts its own straight.
        for following in range(value, value + group_size):
            if counts[following] < starting:
                return False
            counts[following] -= starting
    return True
