"""Depth-first search labels the connected components of a museum: rooms joined by open doorways.

The same labels come out of a recursive search and of one that keeps its own stack."""

doorways = {
    "atrium": ["gallery", "shop"],
    "gallery": ["atrium", "sculpture"],
    "sculpture": ["gallery"],
    "shop": ["atrium"],
    "cafe": ["terrace"],
    "terrace": ["cafe"],
    "vault": [],
}


def label_recursively() -> dict[str, int]:
    label: dict[str, int] = {}

    def visit(room: str, number: int) -> None:
        label[room] = number
        for nearby in doorways[room]:
            if nearby not in label:
                visit(nearby, number)

    for room in doorways:
        if room not in label:  # an unlabelled room starts a new component
            visit(room, len(set(label.values())))
    return label


def label_with_a_stack() -> dict[str, int]:
    label: dict[str, int] = {}
    components = 0
    for room in doorways:
        if room in label:
            continue
        label[room] = components
        stack = [room]
        while stack:
            current = stack.pop()
            for nearby in doorways[current]:
                if nearby not in label:
                    label[nearby] = components
                    stack.append(nearby)
        components += 1
    return label


recursive = label_recursively()
print("labels:", recursive)
print("same labels with a stack:", recursive == label_with_a_stack())
print("components:", len(set(recursive.values())))
print("can you walk from shop to sculpture?", recursive["shop"] == recursive["sculpture"])
print("can you walk from shop to terrace?", recursive["shop"] == recursive["terrace"])
