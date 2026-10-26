def character_replacement(s: str, k: int) -> int:
    best = 0
    for start in range(len(s)):
        counts = [0] * 26
        most = 0
        for end in range(start, len(s)):
            letter = ord(s[end]) - 65
            counts[letter] += 1
            if counts[letter] > most:
                most = counts[letter]
            if end - start + 1 - most > k:
                break
            if end - start + 1 > best:
                best = end - start + 1
    return best
