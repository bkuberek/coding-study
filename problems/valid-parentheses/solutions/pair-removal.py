PAIRS = ("()", "[]", "{}")


def is_valid(s: str) -> bool:
    while True:
        shorter = s
        for pair in PAIRS:
            shorter = shorter.replace(pair, "")
        if len(shorter) == len(s):
            # Nothing left to delete: balanced exactly when nothing is left at all.
            return not s
        s = shorter
