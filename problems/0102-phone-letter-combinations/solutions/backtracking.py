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
    words: list[str] = []
    letters = [""] * len(digits)

    def fill(slot: int) -> None:
        if slot == len(digits):
            words.append("".join(letters))
            return
        for letter in KEYPAD[digits[slot]]:
            letters[slot] = letter
            fill(slot + 1)

    fill(0)
    return words
