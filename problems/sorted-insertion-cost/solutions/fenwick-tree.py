MODULUS = 10**9 + 7


def create_sorted_array(instructions: list[int]) -> int:
    largest = max(instructions)
    # tree[i] (1-based) counts the inserted values in (i - (i & -i), i].
    tree = [0] * (largest + 1)

    def count_at_most(value: int) -> int:
        total = 0
        while value > 0:
            total += tree[value]
            value -= value & -value
        return total

    cost = 0
    for inserted, value in enumerate(instructions):
        less = count_at_most(value - 1)
        greater = inserted - count_at_most(value)
        cost = (cost + min(less, greater)) % MODULUS
        while value <= largest:
            tree[value] += 1
            value += value & -value
    return cost
