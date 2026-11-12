"""Colour a map with three colours so that no two regions that share a border get the same one."""

from itertools import product

BORDERS = {
    "North": ["East", "West", "Centre"],
    "South": ["East", "West", "Centre", "Harbour"],
    "Harbour": ["East", "South"],
    "East": ["North", "South", "Centre", "Harbour"],
    "West": ["North", "South", "Centre"],
    "Centre": ["North", "East", "South", "West"],
}
COLOURS = ["red", "green", "blue"]


def clash(region: str, colour: str, colour_of: dict[str, str]) -> str | None:
    """The first neighbour of region that already has this colour, if any."""
    return next((other for other in BORDERS[region] if colour_of.get(other) == colour), None)


def first_colouring(order: list[str]) -> dict[str, str] | None:
    """Colour the regions in this order, printing every choice, every clash and every undo."""
    colour_of: dict[str, str] = {}

    def place(index: int) -> bool:
        if index == len(order):  # every region has a colour: a solution
            return True
        region, indent = order[index], "  " * index
        for colour in COLOURS:
            neighbour = clash(region, colour, colour_of)
            if neighbour is not None:  # prune: no colouring that starts this way can work
                print(f"{indent}{region} = {colour}: clashes with {neighbour}")
                continue
            print(f"{indent}{region} = {colour}")
            colour_of[region] = colour  # choose
            if place(index + 1):  # explore
                return True
            del colour_of[region]  # undo, so the next colour starts from a clean map
            print(f"{indent}undo {region} = {colour}: nothing fits after it")
        return False

    return dict(colour_of) if place(0) else None


def count_colourings(order: list[str], undo: bool = True) -> tuple[int, int]:
    """(colourings found, choices tried), checking each choice as soon as it is made."""
    colour_of: dict[str, str] = {}
    found = tried = 0

    def place(index: int) -> None:
        nonlocal found, tried
        if index == len(order):
            found += 1
            return
        region = order[index]
        for colour in COLOURS:
            tried += 1
            if clash(region, colour, colour_of) is None:
                colour_of[region] = colour
                place(index + 1)
                if undo:
                    del colour_of[region]

    place(0)
    return found, tried


def count_complete_colourings() -> tuple[int, int]:
    """(colourings found, complete colourings checked), checking only finished maps."""
    regions = list(BORDERS)
    found = checked = 0
    for colours in product(COLOURS, repeat=len(regions)):
        checked += 1
        colour_of = dict(zip(regions, colours, strict=True))
        if all(clash(region, colour_of[region], colour_of) is None for region in regions):
            found += 1
    return found, checked


order = list(BORDERS)  # North, South, Harbour, East, West, Centre
print("found:", first_colouring(order))
found, tried = count_colourings(order)
print(f"checking each choice: {found} found, {tried} choices tried")
found, checked = count_complete_colourings()
print(f"checking complete maps: {found} found, {checked} maps checked")
found, tried = count_colourings(["Centre", "East", "South", "North", "West", "Harbour"])
print(f"Centre first: {found} found, {tried} choices tried")
found, tried = count_colourings(order, undo=False)
print(f"without the undo: {found} found, {tried} choices tried")
