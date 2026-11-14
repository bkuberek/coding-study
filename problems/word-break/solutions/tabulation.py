def word_break(s: str, word_dict: list[str]) -> bool:
    words = set(word_dict)
    longest = max(len(word) for word in word_dict)
    # ok[i] is True when the prefix s[:i] can be split into dictionary words.
    ok = [False] * (len(s) + 1)
    ok[0] = True
    for end in range(1, len(s) + 1):
        for start in range(max(0, end - longest), end):
            if ok[start] and s[start:end] in words:
                ok[end] = True
                break
    return ok[len(s)]
