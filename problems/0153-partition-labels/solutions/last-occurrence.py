def partition_labels(s: str) -> list[int]:
    last = {letter: index for index, letter in enumerate(s)}
    sizes = []
    start = end = 0
    for index, letter in enumerate(s):
        end = max(end, last[letter])
        if index == end:
            # Every letter seen since `start` has no copy after this point: cut here.
            sizes.append(end - start + 1)
            start = index + 1
    return sizes
