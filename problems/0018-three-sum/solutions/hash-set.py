def three_sum(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    triples = []
    for i in range(len(values) - 2):
        if i > 0 and values[i] == values[i - 1]:
            continue
        seen: set[int] = set()
        last_largest = None
        for j in range(i + 1, len(values)):
            middle = -values[i] - values[j]
            if middle in seen and values[j] != last_largest:
                triples.append([values[i], middle, values[j]])
                last_largest = values[j]
            seen.add(values[j])
    return triples
