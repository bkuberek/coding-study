"""What Python's dict and set accept as keys, and the order a dict keeps."""

from dataclasses import dataclass

stock = {"apples": 3, "pears": 5, "plums": 1}
stock["apples"] = 4  # updating a key keeps its place
del stock["pears"]
stock["pears"] = 2  # a key added again goes to the end
print("insertion order:", list(stock))

for candidate in ([1, 2], {"a": 1}, {1, 2}):
    try:
        {candidate: "value"}
    except TypeError:
        print(f"{type(candidate).__name__:>5} as a key: TypeError, not hashable")
print("tuple as a key:", {(1, 2): "value"}[(1, 2)])


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)


print("Point overrides __eq__ only, so its __hash__ is", Point.__hash__)


@dataclass(frozen=True)
class FrozenPoint:
    x: int
    y: int


visited = {FrozenPoint(0, 0), FrozenPoint(0, 0), FrozenPoint(1, 2)}
print("a frozen dataclass is hashable; the set holds", len(visited), "points")
