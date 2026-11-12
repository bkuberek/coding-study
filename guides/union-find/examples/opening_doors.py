"""Union-find with union by size and path compression, on the rooms of a game level.

Doors open one at a time, and between openings the game asks whether two rooms are joined."""


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}  # a root is its own parent
        self.size = dict.fromkeys(items, 1)  # kept up to date for roots only

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:  # first walk: up to the root
            root = self.parent[root]
        while self.parent[item] != root:  # second walk: point everything on the way at the root
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a: str, b: str) -> bool:
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False  # already joined
        if self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a  # hang the smaller tree under the larger one's root
        self.size[root_a] += self.size[root_b]
        return True

    def depth(self, item: str) -> int:
        steps = 0
        while self.parent[item] != item:
            item, steps = self.parent[item], steps + 1
        return steps


rooms = UnionFind(list("abcdefgh"))
for a, b in [("a", "b"), ("c", "d"), ("a", "c"), ("e", "f"), ("g", "h"), ("e", "g")]:
    rooms.union(a, b)
    print(f"open {a}-{b}: parents {rooms.parent}")
print("b and f joined?", rooms.find("b") == rooms.find("f"))
print("open a-e, a new door:", rooms.union("a", "e"))

print("parents:", rooms.parent)
print("depth of h before a find:", rooms.depth("h"))
print("b and h joined?", rooms.find("b") == rooms.find("h"))
print("parents:", rooms.parent)
print("depth of h after it:", rooms.depth("h"), "| depth of g:", rooms.depth("g"))
print("open d-h, a new door:", rooms.union("d", "h"))
