from functools import cache


def word_break(s: str, word_dict: list[str]) -> bool:
    @cache
    def can_split_from(start: int) -> bool:
        # Can the suffix s[start:] be split into dictionary words?
        if start == len(s):
            return True
        for word in word_dict:
            if s.startswith(word, start) and can_split_from(start + len(word)):
                return True
        return False

    return can_split_from(0)
