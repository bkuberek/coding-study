"""Mapping links between three schemes, and what transitivity does to one mistaken link.

SKOS declares `skos:exactMatch` symmetric and transitive, and `skos:closeMatch` symmetric only.
Two people each add one exact match that looks right on its own; following the links as far as
transitivity allows then joins concepts that nobody matched.
"""

exact_matches = [
    ("zoo:crane", "encyclopedia:crane"),  # the bird, in a zoo's scheme and an encyclopedia's
    ("encyclopedia:crane", "machines:crane"),  # a mistake: the lifting machine of the same name
    ("zoo:heron", "encyclopedia:heron"),
]

links: dict[str, set[str]] = {}
for first, second in exact_matches:  # symmetric: store both directions
    links.setdefault(first, set()).add(second)
    links.setdefault(second, set()).add(first)


def one_step(concept: str) -> list[str]:
    return sorted(links.get(concept, ()))


def transitive(concept: str) -> list[str]:
    seen, stack = {concept}, [concept]
    while stack:
        for nxt in links.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(seen - {concept})


print("stated matches of zoo:crane:", one_step("zoo:crane"))
print("entailed matches of zoo:crane:", transitive("zoo:crane"))
print("entailed matches of zoo:heron:", transitive("zoo:heron"))
