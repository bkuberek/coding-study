"""Read two small N-Triples documents into sets of triples, and merge them without mixing blank nodes.

A term is an IRI `<...>`, a blank node `_:label`, or a literal `"text"` with an optional
`@language` or `^^<datatype>`. A graph is a set, so a repeated line adds nothing. Two literals
with different lexical forms are different terms even when they denote the same number. Blank
node labels are local to their document, so a merge renames them apart.
"""

import re

TERM = r'<[^>]*>|_:[A-Za-z0-9]+|"[^"]*"(?:@[a-z-]+|\^\^<[^>]*>)?'
LINE = re.compile(rf"({TERM})\s+({TERM})\s+({TERM})\s*\.")
XSD = "http://www.w3.org/2001/XMLSchema#"

library = f"""
<https://ex.org/b1> <https://ex.org/title> "Sea Charts"@en .
<https://ex.org/b1> <https://ex.org/pages> "412"^^<{XSD}integer> .
<https://ex.org/b1> <https://ex.org/pages> "0412"^^<{XSD}integer> .
<https://ex.org/b1> <https://ex.org/author> _:p .
_:p <https://ex.org/name> "Frank" .
<https://ex.org/b1> <https://ex.org/title> "Sea Charts"@en .
"""
shop = """
<https://ex.org/b2> <https://ex.org/author> _:p .
_:p <https://ex.org/name> "Ursula" .
"""


def parse(document: str) -> set[tuple[str, str, str]]:
    triples = set()
    for line in document.strip().splitlines():
        match = LINE.fullmatch(line.strip())
        if match is None:
            raise ValueError(f"not a triple: {line}")
        triples.add(match.groups())
    return triples


def rename_blanks(triples: set, suffix: str) -> set:
    def term(t: str) -> str:
        return f"{t}{suffix}" if t.startswith("_:") else t
    return {(term(s), p, term(o)) for s, p, o in triples}


first, second = parse(library), parse(shop)
print("lines in the first document:", len(library.strip().splitlines()), "| triples:", len(first))
pages = sorted(o for s, p, o in first if p == "<https://ex.org/pages>")
print("pages terms:", pages)
print("pages values:", sorted({int(o.split('"')[1]) for o in pages}))


def names_per_author(graph: set) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for s, p, o in sorted(graph):
        if p == "<https://ex.org/name>":
            names.setdefault(s, []).append(o)
    return names


print("naive union:", names_per_author(first | second))
merged = rename_blanks(first, "a") | rename_blanks(second, "b")
print("renamed apart:", names_per_author(merged))
