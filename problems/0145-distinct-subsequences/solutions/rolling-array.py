def num_distinct(s: str, t: str) -> int:
    # ways[j] counts the occurrences of t[:j] in the prefix of s read so far.
    ways = [1] + [0] * len(t)
    for character in s:
        # Right to left: ways[j - 1] still excludes this character, so it is used once.
        for j in range(len(t), 0, -1):
            if t[j - 1] == character:
                ways[j] += ways[j - 1]
    return ways[len(t)]
