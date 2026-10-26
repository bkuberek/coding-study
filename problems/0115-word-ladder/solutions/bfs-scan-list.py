from collections import deque


def _one_apart(first: str, second: str) -> bool:
    differences = 0
    for a, b in zip(first, second):
        if a != b:
            differences += 1
            if differences > 1:
                return False
    return differences == 1


def ladder_length(begin_word: str, end_word: str, word_list: list[str]) -> int:
    if end_word not in word_list:
        return 0
    unvisited = [word for word in word_list if word != begin_word]
    queue = deque([(begin_word, 1)])
    while queue:
        word, words_so_far = queue.popleft()
        if word == end_word:
            return words_so_far
        # Compare against every word not reached yet; the neighbors leave the list.
        remaining = []
        for candidate in unvisited:
            if _one_apart(word, candidate):
                queue.append((candidate, words_so_far + 1))
            else:
                remaining.append(candidate)
        unvisited = remaining
    return 0
