import string


def ladder_length(begin_word: str, end_word: str, word_list: list[str]) -> int:
    available = set(word_list)
    if end_word not in available:
        return 0
    available -= {begin_word, end_word}
    # Two frontiers grow toward each other; words counts the ladder length covered so far.
    near, far = {begin_word}, {end_word}
    words = 1
    while near and far:
        if len(near) > len(far):
            near, far = far, near  # always expand the smaller frontier
        words += 1
        following_level = set()
        for word in near:
            for position in range(len(word)):
                prefix, suffix = word[:position], word[position + 1 :]
                for letter in string.ascii_lowercase:
                    candidate = prefix + letter + suffix
                    if candidate in far:
                        return words
                    if candidate in available:
                        available.remove(candidate)
                        following_level.add(candidate)
        near = following_level
    return 0
