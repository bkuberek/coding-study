"""A reader and a writer: keep the wanted values at the front of the same list, in order."""


def keep_at_least(readings: list[int], limit: int) -> int:
    """Move the readings of at least `limit` to the front, in order; return how many there are."""
    write = 0
    for read in range(len(readings)):
        if readings[read] >= limit:
            readings[write] = readings[read]  # write <= read: no unread value is overwritten
            write += 1
    return write


readings = [7, -2, 5, -1, -3, 8, 0]
kept = keep_at_least(readings, 0)
print("after the pass:", readings, "| kept:", kept)
del readings[kept:]
print("truncated:     ", readings)

naive = [7, -2, -1, 5]
for value in naive:  # removing from the list being looped over
    if value < 0:
        naive.remove(value)
print("removing while looping:", naive)


def dedupe_sorted(values: list[int]) -> int:
    """Keep one copy of each value of a sorted list at its front; return how many."""
    write = 0
    for read in range(len(values)):
        keep = write == 0 or values[read] != values[write - 1]  # compare with the last value kept
        print(f"  read={read} write={write} value={values[read]}: {'keep' if keep else 'skip'}")
        if keep:
            values[write] = values[read]
            write += 1
    return write


values = [1, 1, 2, 3, 3, 3, 5]
print("dedupe", values)
size = dedupe_sorted(values)
print("result:", values[:size], "| the tail still holds", values[size:])


def at_most_two(values: list[int], against_kept: bool) -> list[int]:
    """Keep at most two copies of each value of a sorted list."""
    write = 0
    for read in range(len(values)):
        if read >= 2:  # then write >= 2 too, since the first two values are always kept
            earlier = values[write - 2] if against_kept else values[read - 2]
            if values[read] == earlier:
                continue
        values[write] = values[read]
        write += 1
    return values[:write]


print("at most two, compared with what was kept:", at_most_two([1, 1, 1, 2, 2, 3], True))
print("at most two, compared with what was read:", at_most_two([1, 1, 1, 2, 2, 3], False))
