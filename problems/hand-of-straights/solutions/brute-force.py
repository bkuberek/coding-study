def is_n_straight_hand(hand: list[int], group_size: int) -> bool:
    if len(hand) % group_size != 0:
        return False
    cards = sorted(hand)
    while cards:
        # The smallest card must start a straight; remove that straight card by card.
        smallest = cards.pop(0)
        for value in range(smallest + 1, smallest + group_size):
            try:
                cards.remove(value)
            except ValueError:
                return False
    return True
