from collections import Counter, deque


def is_n_straight_hand(hand: list[int], group_size: int) -> bool:
    if len(hand) % group_size != 0:
        return False
    counts = Counter(hand)
    open_count = 0  # straights started but not yet complete; each needs the current value
    opened: deque[int] = deque()  # straights opened at each of the last group_size values
    previous = None
    for value in sorted(counts):
        if open_count > 0 and value != previous + 1:
            return False  # an open straight needs previous + 1, which is missing
        if counts[value] < open_count:
            return False
        new = counts[value] - open_count
        opened.append(new)
        open_count += new
        if len(opened) == group_size:
            # The straights opened group_size values ago end with this value.
            open_count -= opened.popleft()
        previous = value
    return open_count == 0
