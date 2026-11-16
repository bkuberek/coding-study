"""Color a map with three colors so that no two regions that share a border get the same one."""

from itertools import product

BORDERS = {
    "North": ["East", "West", "Center"],
    "South": ["East", "West", "Center", "Harbor"],
    "Harbor": ["East", "South"],
    "East": ["North", "South", "Center", "Harbor"],
    "West": ["North", "South", "Center"],
    "Center": ["North", "East", "South", "West"],
}
COLORS = ["red", "green", "blue"]


def clash(region: str, color: str, color_of: dict[str, str]) -> str | None:
    """The first neighbor of region that already has this color, if any."""
    return next((other for other in BORDERS[region] if color_of.get(other) == color), None)


def first_coloring(order: list[str]) -> dict[str, str] | None:
    """Color the regions in this order, printing every choice, every clash and every undo."""
    color_of: dict[str, str] = {}

    def place(index: int) -> bool:
        if index == len(order):  # every region has a color: a solution
            return True
        region, indent = order[index], "  " * index
        for color in COLORS:
            neighbor = clash(region, color, color_of)
            if neighbor is not None:  # prune: no coloring that starts this way can work
                print(f"{indent}{region} = {color}: clashes with {neighbor}")
                continue
            print(f"{indent}{region} = {color}")
            color_of[region] = color  # choose
            if place(index + 1):  # explore
                return True
            del color_of[region]  # undo, so the next color starts from a clean map
            print(f"{indent}undo {region} = {color}: nothing fits after it")
        return False

    return dict(color_of) if place(0) else None


def count_colorings(order: list[str], undo: bool = True) -> tuple[int, int]:
    """(colorings found, choices tried), checking each choice as soon as it is made."""
    color_of: dict[str, str] = {}
    found = tried = 0

    def place(index: int) -> None:
        nonlocal found, tried
        if index == len(order):
            found += 1
            return
        region = order[index]
        for color in COLORS:
            tried += 1
            if clash(region, color, color_of) is None:
                color_of[region] = color
                place(index + 1)
                if undo:
                    del color_of[region]

    place(0)
    return found, tried


def count_complete_colorings() -> tuple[int, int]:
    """(colorings found, complete colorings checked), checking only finished maps."""
    regions = list(BORDERS)
    found = checked = 0
    for colors in product(COLORS, repeat=len(regions)):
        checked += 1
        color_of = dict(zip(regions, colors, strict=True))
        if all(clash(region, color_of[region], color_of) is None for region in regions):
            found += 1
    return found, checked


order = list(BORDERS)  # North, South, Harbor, East, West, Center
print("found:", first_coloring(order))
found, tried = count_colorings(order)
print(f"checking each choice: {found} found, {tried} choices tried")
found, checked = count_complete_colorings()
print(f"checking complete maps: {found} found, {checked} maps checked")
found, tried = count_colorings(["Center", "East", "South", "North", "West", "Harbor"])
print(f"Center first: {found} found, {tried} choices tried")
found, tried = count_colorings(order, undo=False)
print(f"without the undo: {found} found, {tried} choices tried")
