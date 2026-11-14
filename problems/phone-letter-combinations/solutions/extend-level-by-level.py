KEYPAD = {
    "2": "abc",
    "3": "def",
    "4": "ghi",
    "5": "jkl",
    "6": "mno",
    "7": "pqrs",
    "8": "tuv",
    "9": "wxyz",
}


def letter_combinations(digits: str) -> list[str]:
    if not digits:
        return []
    words = [""]
    for digit in digits:
        words = [word + letter for word in words for letter in KEYPAD[digit]]
    return words
