def partition_labels(s: str) -> list[int]:
    sizes = []
    start = 0
    while start < len(s):
        # The piece must reach the last copy of every letter it contains.
        end = s.rfind(s[start])
        position = start
        while position <= end:
            end = max(end, s.rfind(s[position]))
            position += 1
        sizes.append(end - start + 1)
        start = end + 1
    return sizes
