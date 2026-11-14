"""Read the same triples two ways: entailment that adds what must be true, and a closed-world check.

The reasoner applies three RDFS entailment patterns until a pass adds nothing: rdfs5 (a
sub-property of a sub-property is a sub-property), rdfs7 (a triple with a sub-property also
holds with its super-property) and rdfs2 (the subject of a property with a domain is an
instance of the domain). It never concludes that something is false. The check reads the asserted
triples only and treats what is not written as missing.
"""

SUB_PROPERTY, DOMAIN, TYPE = "rdfs:subPropertyOf", "rdfs:domain", "rdf:type"

asserted = {
    (":hasMother", SUB_PROPERTY, ":hasParent"),
    (":hasParent", SUB_PROPERTY, ":hasRelative"),
    (":hasISBN", DOMAIN, ":Book"),
    (":kim", ":hasMother", ":ann"),
    (":charts", TYPE, ":Book"), (":charts", ":title", '"Sea Charts"'),
    (":atlas", TYPE, ":Book"),
    (":talk42", ":hasISBN", '"978-0-00-000000-0"'),  # a data-entry mistake: a talk got an ISBN
}


def entail(graph: set) -> tuple[set, int]:
    closure, passes = set(graph), 0
    while True:
        passes += 1
        new = set()
        for s, p, o in closure:
            for s2, p2, o2 in closure:
                if p == SUB_PROPERTY and p2 == SUB_PROPERTY and o == s2:
                    new.add((s, SUB_PROPERTY, o2))  # rdfs5
                if p == SUB_PROPERTY and p2 == s:
                    new.add((s2, o, o2))  # rdfs7
                if p == DOMAIN and p2 == s:
                    new.add((s2, TYPE, o))  # rdfs2
        if new <= closure:
            return closure, passes
        closure |= new


closure, passes = entail(asserted)
print(f"{len(asserted)} asserted, {len(closure)} in the closure, after {passes} passes")
for triple in sorted(closure - asserted):
    print("  entailed:", " ".join(triple))


def ask(triple: tuple[str, str, str]) -> str:
    return "entailed" if triple in closure else "unknown"


print("kim hasRelative ann?", ask((":kim", ":hasRelative", ":ann")))
print("kim hasRelative bob?", ask((":kim", ":hasRelative", ":bob")), "(not false)")

# A shape: every asserted Book has at least one title. It reads `asserted`, never `closure`.
for book in sorted(s for s, p, o in asserted if p == TYPE and o == ":Book"):
    titles = [o for s, p, o in asserted if s == book and p == ":title"]
    if not titles:
        known = any(s == book and p == ":title" for s, p, o in closure)
        print(f"validator: {book} has 0 :title values, needs at least 1"
              f" | reasoner on {book} :title: {'entailed' if known else 'unknown'}")
print("validator targets :talk42?", (":talk42", TYPE, ":Book") in asserted,
      "| reasoner says :talk42 is a Book:", ask((":talk42", TYPE, ":Book")))
