"""Labels for stock counts, imported by the entry module."""

SEPARATOR = ": "


def label_for(name: str, count: int) -> str:
    return f"{name}{SEPARATOR}{count}"
