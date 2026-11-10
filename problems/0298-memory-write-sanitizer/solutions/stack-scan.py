import re

DELIMITERS = ("<memory>", "</memory>")
DELIMITER_END = ">"
ROLE_MARKER = re.compile(r"[ \t]*(system|assistant|developer|tool):", re.IGNORECASE)
DELIMITERS_REMOVED = "delimiters removed"
TRUNCATED = "truncated"


def sanitize_memory(text: str, max_length: int) -> list[str]:
    cleaned, removed = _remove_delimiters(text)
    flags = [DELIMITERS_REMOVED] if removed else []
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
        flags.append(TRUNCATED)
    flags.extend(_role_marker_flags(cleaned))
    return [cleaned, *flags]


def _remove_delimiters(text: str) -> tuple[str, bool]:
    """The text with no delimiter left in it, even one that a removal joined together.

    Each character goes onto a stack, and a delimiter is popped the moment its last character
    arrives. What sits below the top never changes, so the stack never holds a delimiter.
    """
    kept: list[str] = []
    removed = False
    for character in text:
        kept.append(character)
        if character != DELIMITER_END:
            continue
        for delimiter in DELIMITERS:
            if "".join(kept[-len(delimiter) :]).lower() == delimiter:
                del kept[-len(delimiter) :]
                removed = True
                break
    return "".join(kept), removed


def _role_marker_flags(text: str) -> list[str]:
    flags = []
    for number, line in enumerate(text.split("\n"), start=1):
        if marker := ROLE_MARKER.match(line):
            flags.append(f"line {number}: {marker.group(1).lower()}")
    return flags
