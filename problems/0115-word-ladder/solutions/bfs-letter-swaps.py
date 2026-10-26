import string
from collections import deque


def ladder_length(begin_word: str, end_word: str, word_list: list[str]) -> int:
    # Words still available; a word leaves the set the moment it is reached.
    available = set(word_list)
    if end_word not in available:
        return 0
    available.discard(begin_word)
    queue = deque([(begin_word, 1)])
    while queue:
        word, words_so_far = queue.popleft()
        if word == end_word:
            return words_so_far
        for position in range(len(word)):
            prefix, suffix = word[:position], word[position + 1 :]
            for letter in string.ascii_lowercase:
                candidate = prefix + letter + suffix
                if candidate in available:
                    available.remove(candidate)
                    queue.append((candidate, words_so_far + 1))
    return 0
