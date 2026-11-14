def longest_palindrome(s: str) -> str:
    # Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
    t = "|" + "|".join(s) + "|"
    # radius[i] is how far the palindrome centered at t[i] extends to each side.
    radius = [0] * len(t)
    center = right = 0  # the palindrome reaching furthest right is t[2 * center - right .. right]
    for i in range(len(t)):
        if i < right:
            # Mirror of i around center; its radius is valid up to the right boundary.
            radius[i] = min(right - i, radius[2 * center - i])
        while (
            i - radius[i] - 1 >= 0
            and i + radius[i] + 1 < len(t)
            and t[i - radius[i] - 1] == t[i + radius[i] + 1]
        ):
            radius[i] += 1
        if i + radius[i] > right:
            center, right = i, i + radius[i]
    best = max(range(len(t)), key=radius.__getitem__)
    # A radius r around position i of t covers r characters of s starting at (i - r) // 2.
    start = (best - radius[best]) // 2
    return s[start : start + radius[best]]
