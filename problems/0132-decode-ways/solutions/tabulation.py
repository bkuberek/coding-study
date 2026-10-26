def num_decodings(s: str) -> int:
    # ways[i] is the number of readings of the prefix s[:i]; the empty prefix has one.
    ways = [0] * (len(s) + 1)
    ways[0] = 1
    for i in range(1, len(s) + 1):
        if s[i - 1] != "0":
            ways[i] += ways[i - 1]
        if i >= 2 and 10 <= int(s[i - 2 : i]) <= 26:
            ways[i] += ways[i - 2]
    return ways[len(s)]
