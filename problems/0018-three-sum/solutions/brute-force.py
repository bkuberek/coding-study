def three_sum(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    n = len(values)
    triples = []
    for i in range(n - 2):
        if i > 0 and values[i] == values[i - 1]:
            continue
        for j in range(i + 1, n - 1):
            if j > i + 1 and values[j] == values[j - 1]:
                continue
            third = -values[i] - values[j]
            # The membership test scans values[j + 1:] in C: still one check per element.
            if third in values[j + 1 :]:
                triples.append([values[i], values[j], third])
    return triples
