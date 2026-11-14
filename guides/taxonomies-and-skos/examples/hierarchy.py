"""A small concept scheme with two parents for one concept, read the way SKOS defines its links.

`skos:broader` states direct links only. SKOS makes it a sub-property of `skos:broaderTransitive`,
which is transitive, and `skos:narrower` the inverse of `skos:broader`; applying those rules
until nothing new appears gives every ancestor. Labels: one preferred label per language, any
number of alternative labels, and hidden labels that search can match but nobody is shown.
"""

broader = {  # concept -> its direct broader concepts
    "amphibious-car": {"car", "boat"},
    "car": {"land-vehicle"},
    "boat": {"watercraft"},
    "land-vehicle": {"vehicle"},
    "watercraft": {"vehicle"},
    "hovercraft": {"watercraft", "vehicle"},
    "vehicle": set(),
}
labels = {
    "amphibious-car": {"pref": "Amphibious car", "alt": ["Car-boat"],
                       "hidden": ["amfibious car"]},
    "boat": {"pref": "Boat", "alt": ["Vessel"], "hidden": []},
}

narrower: dict[str, set[str]] = {concept: set() for concept in broader}
for concept, parents in broader.items():  # skos:narrower is the inverse of skos:broader
    for parent in parents:
        narrower[parent].add(concept)

transitive = {concept: set(parents) for concept, parents in broader.items()}
rounds = 0
while True:  # broaderTransitive: a link of a link is a link, until nothing new appears
    rounds += 1
    added = {(c, g) for c, ps in transitive.items() for p in ps for g in transitive[p]
             if g not in ps}
    if not added:
        break
    for concept, ancestor in added:
        transitive[concept].add(ancestor)

print("broader(amphibious-car):", sorted(broader["amphibious-car"]))
print("broaderTransitive(amphibious-car):", sorted(transitive["amphibious-car"]),
      f"after {rounds} rounds")
print("narrower(vehicle):", sorted(narrower["vehicle"]))


def paths_up(concept: str) -> list[list[str]]:
    if not broader[concept]:
        return [[concept]]
    return [[concept, *path] for parent in sorted(broader[concept]) for path in paths_up(parent)]


for path in paths_up("amphibious-car") + paths_up("hovercraft"):
    print(f"path of {len(path) - 1}:", " -> ".join(path))


def search(text: str) -> list[str]:
    wanted = text.casefold()
    return sorted(concept for concept, entry in labels.items()
                  if wanted in {entry["pref"].casefold(), *map(str.casefold, entry["alt"]),
                                *map(str.casefold, entry["hidden"])})


for query in ["vessel", "amfibious car", "Amphibious car"]:
    print(f"search {query!r}:", search(query))
