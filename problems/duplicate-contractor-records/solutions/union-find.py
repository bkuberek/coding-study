import re

LEGAL_FORMS = frozenset({"co", "company", "corp", "inc", "incorporated", "llc", "ltd"})
SEPARATORS = re.compile(r"[^a-z0-9]+")
TAX_ID_DIGITS = 9


def duplicate_groups(names: list[str], tax_ids: list[str]) -> list[list[int]]:
    parent = list(range(len(names)))

    def find(record: int) -> int:
        while parent[record] != record:
            parent[record] = parent[parent[record]]  # path halving
            record = parent[record]
        return record

    first_with_key: dict[tuple[str, str], int] = {}
    for record, (name, tax_id) in enumerate(zip(names, tax_ids, strict=True)):
        for key in (("name", normalize_name(name)), ("tax", normalize_tax_id(tax_id))):
            if not key[1]:
                continue  # an empty key matches nothing
            if key in first_with_key:
                parent[find(record)] = find(first_with_key[key])
            else:
                first_with_key[key] = record
    groups: dict[int, list[int]] = {}
    for record in range(len(names)):
        groups.setdefault(find(record), []).append(record)  # insertion order = smallest index first
    return [members for members in groups.values() if len(members) > 1]


def normalize_name(name: str) -> str:
    tokens = [token for token in SEPARATORS.split(name.lower()) if token]
    while tokens and tokens[-1] in LEGAL_FORMS:
        tokens.pop()
    return " ".join(tokens)


def normalize_tax_id(tax_id: str) -> str:
    digits = "".join(character for character in tax_id if "0" <= character <= "9")
    return digits if len(digits) == TAX_ID_DIGITS else ""
